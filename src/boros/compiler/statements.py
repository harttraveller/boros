"""Compilation of statements and blocks.

Every statement compiles to a closure `run(fr)` over the frame dict `fr`.
It returns None when the statement completes normally, or one of the
signals BREAK, CONTINUE and RETURN, which travel outwards through the
enclosing block closures until a loop (break/continue) or the function body
(return) acts on them.  A `return` stores its value in `fr['.rv']` before
returning the RETURN signal.

Interpreted exceptions are ordinary host exceptions.  Closures that run
several statements (blocks, loops, if statements) catch them on the way out
just long enough to record the line of the statement that failed with
runtime.errors.annotate; these records become the interpreted traceback.

A compile function often chooses between several closure variants (for
example an assignment to a local variable is cheaper than one to an
attribute).  Each variant is built by a small `make_*` factory, so that the
code that runs at run time stays short and does no work that could have
been done at compile time.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, cast

from ..lexer import syntax_error
from ..runtime.attributes import getattr_any, inst_setattr, setattr_any
from ..runtime.errors import annotate, exc_value, unbound_free, unbound_local
from ..runtime.exceptions import (
    NOT_AN_EXCEPTION,
    CatchAll,
    exc_matches,
    getattr_special,
    star_match,
    star_result,
    to_native_exc,
)
from ..runtime.lookup import K_MISSING
from ..runtime.modules import import_module, module_dict, module_for
from ..runtime.objects import BREAK, CONTINUE, RETURN, Instance
from ..runtime.protocols import context_methods, exc_type
from ..runtime.typechecks import type_name
from ..syntax import (
    COMPOUND,
    AnnAssign,
    Assign,
    Attribute,
    ClassDef,
    Const,
    ExceptHandler,
    ExprStmt,
    FunctionDef,
    Global,
    MatchCase,
    Name,
    Nonlocal,
    Pass,
    Return,
    Subscript,
    Tuple,
)
from .names import compile_const, load_name, store_name, unbind_name
from .operators import INPLACE_OPS
from .scopes import CLASSNS, GLOBAL, LOCAL
from .targets import del_target, target

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core_types import ExprFn, Frame, StmtFn, StoreFn
    from ..runtime.objects import Signal
    from ..syntax import (
        Assert,
        AugAssign,
        Break,
        Continue,
        Delete,
        Expression,
        For,
        If,
        Import,
        ImportFrom,
        Raise,
        Statement,
        Try,
        While,
        With,
        WithItem,
    )
    from .compiler import Compiler

    Handler = tuple[ExprFn | None, StoreFn | None, Callable[[Frame], None], Callable[[Frame], Any]]
    """A compiled `except` clause: (exception type or None for a bare except,
    store for the `as` name or None, unbind for the `as` name, handler body).
    The body is a StmtFn here and a GenFn in generator mode."""

    Where = tuple[int, str, str]
    """A place in the source, for a traceback: (line, function name, filename)."""


# -- statement lists ---------------------------------------------------------------


def noop(fr: Frame) -> None:
    """The compiled form of `pass` and of an empty statement list."""


def is_docstring(s: Statement) -> bool:
    """Is s a string constant on its own, as at the start of a docstring?"""
    return type(s) is ExprStmt and type(s.value) is Const and type(s.value.value) is str


def docstring_text(s: Statement) -> str | None:
    """The docstring that statement s is, if it is a string constant on its
    own, with its indentation removed (see clean_doc)."""
    if type(s) is ExprStmt and type(s.value) is Const and type(s.value.value) is str:
        return clean_doc(s.value.value)
    return None


def clean_doc(doc: str) -> str:
    """A docstring with its indentation removed, as the Python 3.13 compiler
    does: tabs are expanded, the first line loses its leading spaces, and
    the common leading spaces of the other non-blank lines are removed."""
    if '\n' not in doc and '\t' not in doc and doc[:1] != ' ':
        return doc
    lines: list[str] = doc.expandtabs().split('\n')
    indents: list[int] = [len(ln) - len(ln.lstrip(' ')) for ln in lines]
    margin: int = min([k for k, ln in zip(indents[1:], lines[1:]) if k < len(ln)], default=0)
    out: list[str] = [lines[0][indents[0]:]]
    for k, ln in zip(indents[1:], lines[1:]):
        out.append(ln[min(k, margin):])
    return '\n'.join(out)


def real_statements(stmts: list[Statement]) -> list[Statement]:
    """The statements of stmts that do something when run.

    `pass`, `global` and `nonlocal` (whose effect is on name resolution at
    compile time) and bare constants such as docstrings are dropped."""
    out: list[Statement] = []
    for s in stmts:
        t: type[Statement] = type(s)
        if t is Pass or t is Global or t is Nonlocal:
            continue
        if type(s) is ExprStmt and type(s.value) is Const:
            continue
        out.append(s)
    return out


def block(comp: Compiler, stmts: list[Statement]) -> StmtFn:
    """Compile the body of a compound statement into a single closure.

    An empty body becomes noop and a single statement is used as it is;
    longer bodies are run in order by run_block, which stops at the first
    signal and records the line of a statement that raises."""
    real: list[Statement] = real_statements(stmts)
    cs: list[StmtFn] = [comp.stmt(s) for s in real]
    if not cs:
        return noop
    if len(cs) == 1:
        return cs[0]
    return make_run_block(comp, cs, [s.line for s in real])


def make_run_block(comp: Compiler, cs: list[StmtFn], lines: list[int]) -> StmtFn:
    """Run the statements cs (at source lines `lines`) one after another."""
    name: str = comp.code_name
    filename: str = comp.filename
    first: StmtFn = cs[0]

    def run_block(fr: Frame) -> Signal | None:
        s: StmtFn = first  # bound before the try, so the handler can always use it
        try:
            for s in cs:
                r: Signal | None = s(fr)
                if r is not None:
                    return r
        except BaseException as e:
            annotate(e, fr, lines[cs.index(s)], name, filename)
            raise
        return None
    return run_block


def body_line(comp: Compiler, stmts: list[Statement], header: int) -> int:
    """The line a compound statement reports when its body raises: the line
    of the body if that is a single simple statement, else the header line."""
    real: list[Statement] = real_statements(stmts)
    if len(real) == 1 and type(real[0]) not in COMPOUND:
        return real[0].line
    return header


def module_body(comp: Compiler, stmts: list[Statement]) -> StmtFn:
    """Compile module-level statements.  Unlike block() this always records
    traceback lines, since there is no enclosing function call to do it.
    A module docstring is stored in `__doc__` before they run."""
    real: list[Statement] = real_statements(stmts)
    cs: list[StmtFn] = [comp.stmt(s) for s in real]
    lines: list[int] = [s.line for s in real]
    if has_annotations(stmts):
        cs.insert(0, setup_annotations)
        lines.insert(0, lines[0])
    name: str = comp.code_name
    filename: str = comp.filename
    doc: str | None = docstring_text(stmts[0]) if stmts else None

    def run_module(fr: Frame) -> None:
        if doc is not None:
            fr['__doc__'] = doc
        for s in cs:
            try:
                s(fr)
            except BaseException as e:
                annotate(e, fr, lines[cs.index(s)], name, filename)
                raise
    return run_module


def has_annotations(stmts: list[Any]) -> bool:
    """Whether a module or class body contains an annotated assignment,
    possibly inside compound statements but not inside a nested function or
    class.  Such a body creates its `__annotations__` dict when it starts."""
    for s in stmts:
        t: type = type(s)
        if t is AnnAssign:
            return True
        if (t in COMPOUND and t is not FunctionDef and t is not ClassDef) or t is ExceptHandler or t is MatchCase:
            for f in t._fields:
                v: Any = getattr(s, f)
                if type(v) is list and has_annotations(v):
                    return True
    return False


def setup_annotations(fr: Frame) -> None:
    """The statement that starts a module or class body with annotated
    assignments: give its namespace an `__annotations__` dict if it has none."""
    if '__annotations__' not in fr:
        fr['__annotations__'] = {}


# -- function bodies -----------------------------------------------------------------


def function_body(comp: Compiler, stmts: list[Statement]) -> ExprFn:
    """Compile a function body into a closure run(fr) that returns the
    function's return value.

    A `return` inside the body stores its value in fr['.rv'] and returns
    the RETURN signal; a final `return` at the end of the body is compiled
    as a plain expression instead, so the common case needs no signal."""
    real, retc = split_final_return(comp, real_statements(stmts))
    cs: list[StmtFn] = [comp.stmt(s) for s in real]
    lines: list[int] = [s.line for s in real]
    if not cs:
        if retc is None:
            return noop
        return retc
    if retc is None:
        if len(cs) == 1:
            return make_run_one(cs[0])
        return make_run_body(comp, cs, lines)
    return make_run_body_ret(comp, cs, lines, retc)


def split_final_return(comp: Compiler, real: list[Statement]) -> tuple[list[Statement], ExprFn | None]:
    """Split a trailing `return` off a function body: returns the other
    statements and the compiled return value (None if there is no final
    return)."""
    if real:
        last: Statement = real[-1]
        if type(last) is Return:
            if last.value is None:
                return real[:-1], compile_const(comp, Const(last.line, None))
            return real[:-1], comp.expr(last.value)
    return real, None


def make_run_one(s0: StmtFn) -> ExprFn:
    """A function body of one statement and no final return."""
    def run_one(fr: Frame) -> Any:
        if s0(fr) is not None:
            return fr['.rv']
        return None
    return run_one


def make_run_body(comp: Compiler, cs: list[StmtFn], lines: list[int]) -> ExprFn:
    """A function body of several statements and no final return."""
    name: str = comp.code_name
    filename: str = comp.filename
    first: StmtFn = cs[0]

    def run_body(fr: Frame) -> Any:
        s: StmtFn = first  # bound before the try, so the handler can always use it
        try:
            for s in cs:
                if s(fr) is not None:
                    return fr['.rv']
        except BaseException as e:
            annotate(e, fr, lines[cs.index(s)], name, filename)
            raise
        return None
    return run_body


def make_run_body_ret(comp: Compiler, cs: list[StmtFn], lines: list[int], retc: ExprFn) -> ExprFn:
    """A function body of statements followed by a final `return retc`."""
    name: str = comp.code_name
    filename: str = comp.filename
    first: StmtFn = cs[0]

    def run_body_ret(fr: Frame) -> Any:
        s: StmtFn = first  # bound before the try, so the handler can always use it
        try:
            for s in cs:
                if s(fr) is not None:
                    return fr['.rv']
        except BaseException as e:
            annotate(e, fr, lines[cs.index(s)], name, filename)
            raise
        return retc(fr)
    return run_body_ret


# -- simple statements ---------------------------------------------------------------


def compile_expr_stmt(comp: Compiler, s: ExprStmt) -> StmtFn:
    """An expression evaluated for its side effects."""
    c: ExprFn = comp.expr(s.value)

    def expr_stmt(fr: Frame) -> None:
        c(fr)
    return expr_stmt


def compile_pass(comp: Compiler, s: Statement) -> StmtFn:
    """`pass` (also used for `global` and `nonlocal`)."""
    return noop


def compile_break(comp: Compiler, s: Break) -> StmtFn:
    """`break`: signal the enclosing loop to stop."""
    def break_(fr: Frame) -> Signal:
        return BREAK
    return break_


def compile_continue(comp: Compiler, s: Continue) -> StmtFn:
    """`continue`: signal the enclosing loop to start its next iteration."""
    def continue_(fr: Frame) -> Signal:
        return CONTINUE
    return continue_


def compile_return(comp: Compiler, s: Return) -> StmtFn:
    """`return value`: store the value in fr['.rv'] and signal RETURN."""
    if comp.stack[-1].kind != 'function':
        raise syntax_error("'return' outside function", comp.filename, s.line)
    if s.value is None:
        def return_none(fr: Frame) -> Signal:
            fr['.rv'] = None
            return RETURN
        return return_none
    vc: ExprFn = comp.expr(s.value)

    def return_(fr: Frame) -> Signal:
        fr['.rv'] = vc(fr)
        return RETURN
    return return_


def compile_raise(comp: Compiler, s: Raise) -> StmtFn:
    """`raise`, `raise exc` and `raise exc from cause`.  Interpreted
    exception objects are converted to the host exceptions that carry them."""
    if s.exc is None:
        def reraise(fr: Frame) -> None:
            e: BaseException | None = sys.exc_info()[1]
            if e is None:
                raise RuntimeError('No active exception to reraise')
            raise e
        return reraise
    ec: ExprFn = comp.expr(s.exc)
    if s.cause is None:
        def raise_(fr: Frame) -> None:
            raise to_native_exc(ec(fr))
        return raise_
    cc: ExprFn = comp.expr(s.cause)

    def raise_from(fr: Frame) -> None:
        e: BaseException = to_native_exc(ec(fr))
        c: Any = cc(fr)
        if c is None:
            raise e from None
        raise e from native_cause(c)
    return raise_from


def native_cause(c: Any) -> BaseException:
    """The host exception for the cause of `raise exc from c`."""
    try:
        return to_native_exc(c)
    except TypeError as x:
        if x.args != (NOT_AN_EXCEPTION,):
            raise
        raise TypeError('exception causes must derive from BaseException') from None


def compile_assert(comp: Compiler, s: Assert) -> StmtFn:
    """`assert test, msg`."""
    tc: ExprFn = comp.expr(s.test)
    mc: ExprFn | None = comp.expr(s.msg) if s.msg is not None else None

    def assert_(fr: Frame) -> None:
        if not tc(fr):
            if mc is None:
                raise AssertionError()
            raise AssertionError(mc(fr))
    return assert_


def compile_delete(comp: Compiler, s: Delete) -> StmtFn:
    """`del t1, t2, ...`: delete each target in turn."""
    ds: list[StmtFn] = [del_target(comp, t) for t in s.targets]
    if len(ds) == 1:
        return ds[0]

    def delete(fr: Frame) -> None:
        for d in ds:
            d(fr)
    return delete


# -- assignment ------------------------------------------------------------------------


def compile_assign(comp: Compiler, s: Assign) -> StmtFn:
    """`t1 = t2 = ... = value`.

    The common single-target forms get closures that do the store inline:
    a local, class-level or global variable, an attribute, and `fr[k] = v`
    where fr is a parameter and k a variable of the enclosing function (the
    shape of the frame stores in boros's own closures).  Every other target
    goes through the store function made by targets.target."""
    vc: ExprFn = comp.expr(s.value)
    if len(s.targets) != 1:
        return make_assign_multi([target(comp, t) for t in s.targets], vc)
    t: Expression = s.targets[0]
    fast: StmtFn | None = None
    if type(t) is Name:
        fast = assign_name(comp, t, s.value, vc)
    elif type(t) is Attribute:
        fast = make_assign_attr(comp.expr(t.value), t.attr, vc)
    elif type(t) is Subscript:
        fast = assign_subscript(comp, t, s.value, vc)
    if fast is not None:
        return fast
    return make_assign(target(comp, t), vc)


def compile_annassign(comp: Compiler, s: AnnAssign) -> StmtFn:
    """`target: annotation = value`, which runs the assignment first.

    Only a module or class body evaluates the annotation, after the value;
    for a simple name it stores the result in `__annotations__`.  Inside a
    function annotations are never evaluated, so this is a plain assignment
    (or nothing, for a name without a value)."""
    assign: StmtFn = annotated_target(comp, s)
    kind: str = comp.stack[-1].kind
    if kind != 'module' and kind != 'class':
        return assign
    ann: ExprFn = comp.expr(s.annotation)
    if s.simple and type(s.target) is Name:
        return make_annassign(assign, s.target.id, ann)
    return make_annotate_complex(assign, ann)


def annotated_target(comp: Compiler, s: AnnAssign) -> StmtFn:
    """The part of `target: annotation [= value]` that is not about the
    annotation: the assignment of the value, or else, as in CPython,
    evaluating the object (and index) of an attribute or subscript target."""
    t: Expression = s.target
    if s.value is not None:
        return compile_assign(comp, Assign(s.line, [t], s.value))
    if type(t) is Attribute:
        return compile_expr_stmt(comp, ExprStmt(s.line, t.value))
    if type(t) is Subscript:
        return compile_expr_stmt(comp, ExprStmt(s.line, Tuple(s.line, [t.value, t.index])))
    return noop


def make_annassign(assign: StmtFn, name: str, ann: ExprFn) -> StmtFn:
    """`name: annotation [= value]` in a module or class body: assign, then
    record the annotation in the namespace's `__annotations__`."""
    def annassign(fr: Frame) -> None:
        assign(fr)
        v: Any = ann(fr)
        try:
            anns: Any = fr['__annotations__']
        except KeyError:
            raise NameError("name '__annotations__' is not defined", name='__annotations__') from None
        anns[name] = v
    return annassign


def make_annotate_complex(assign: StmtFn, ann: ExprFn) -> StmtFn:
    """An annotated attribute, subscript or parenthesized name in a module or
    class body: the annotation is evaluated but not stored."""
    def annotate_complex(fr: Frame) -> None:
        assign(fr)
        ann(fr)
    return annotate_complex


def assign_name(comp: Compiler, t: Name, value: Expression, vc: ExprFn) -> StmtFn | None:
    """`name = value` for a local, class-level or global name (None for a
    free variable, which needs the generic store)."""
    kind: Signal = comp.resolve(t.id)[0]
    if kind is LOCAL or kind is CLASSNS:
        return assign_local(comp, t.id, value, vc)
    if kind is GLOBAL:
        return make_assign_global(comp.g, t.id, vc)
    return None


def assign_local(comp: Compiler, name: str, value: Expression, vc: ExprFn) -> StmtFn:
    """`name = value` storing into the current frame.  Copying a parameter
    or a variable of the enclosing function is done inline."""
    vk, vname = comp.operand(value)
    if vk == 'param':
        return make_assign_local_param(name, vname)
    if vk == 'free1':
        return make_assign_local_free(name, vname)
    return make_assign_local(name, vc)


def make_assign_local_param(name: str, vname: str) -> StmtFn:
    """`name = param`."""
    def assign_local_param(fr: Frame) -> None:
        fr[name] = fr[vname]
    return assign_local_param


def make_assign_local_free(name: str, vname: str) -> StmtFn:
    """`name = vname` where vname belongs to the enclosing function."""
    def assign_local_free(fr: Frame) -> None:
        try:
            fr[name] = fr['.up'][vname]
        except KeyError:
            raise unbound_free(vname) from None
    return assign_local_free


def make_assign_local(name: str, vc: ExprFn) -> StmtFn:
    """`name = value` into the current frame."""
    def assign_local(fr: Frame) -> None:
        fr[name] = vc(fr)
    return assign_local


def make_assign_global(g: Frame, name: str, vc: ExprFn) -> StmtFn:
    """`name = value` into the module globals g."""
    def assign_global(fr: Frame) -> None:
        g[name] = vc(fr)
    return assign_global


def make_assign_attr(oc: ExprFn, name: str, vc: ExprFn) -> StmtFn:
    """`obj.name = value`.

    For an interpreted instance whose class has no __setattr__ and whose
    attribute lookup cache already records that the class has no attribute
    `name` (so no descriptor can intercept the store), the value goes
    straight into the instance dict."""
    def assign_attr(fr: Frame) -> None:
        v: Any = vc(fr)
        o: Any = oc(fr)
        if type(o) is Instance:
            if o.cls.sethook is None:
                e: tuple[Signal, Any, Any] | None = o.cls.cache.get(name)
                if e is not None and e[0] is K_MISSING:
                    o.d[name] = v
                    return
            inst_setattr(o, name, v)
        else:
            setattr_any(o, name, v)
    return assign_attr


def assign_subscript(comp: Compiler, t: Subscript, value: Expression, vc: ExprFn) -> StmtFn | None:
    """`param[k] = value` where k is a variable of the enclosing function
    (None for any other subscript target, which needs the generic store)."""
    ok, oname = comp.operand(t.value)
    kk, k = comp.operand(t.index)
    if ok != 'param' or kk != 'free1':
        return None
    vk, vname = comp.operand(value)
    if vk == 'local':
        return make_assign_item_local(oname, k, vname)
    return make_assign_item_free(oname, k, vc)


def make_assign_item_local(oname: str, k: str, vname: str) -> StmtFn:
    """`oname[k] = vname` with oname a parameter, k a variable of the
    enclosing function and vname a local variable."""
    def assign_item_local(fr: Frame) -> None:
        try:
            v: Any = fr[vname]
        except KeyError:
            raise unbound_local(vname) from None
        try:
            key: Any = fr['.up'][k]
        except KeyError:
            raise unbound_free(k) from None
        fr[oname][key] = v
    return assign_item_local


def make_assign_item_free(oname: str, k: str, vc: ExprFn) -> StmtFn:
    """`oname[k] = value` with oname a parameter and k a variable of the
    enclosing function."""
    def assign_item(fr: Frame) -> None:
        v: Any = vc(fr)
        try:
            key: Any = fr['.up'][k]
        except KeyError:
            raise unbound_free(k) from None
        fr[oname][key] = v
    return assign_item


def make_assign(store: StoreFn, vc: ExprFn) -> StmtFn:
    """`target = value` through a generic store function."""
    def assign(fr: Frame) -> None:
        store(fr, vc(fr))
    return assign


def make_assign_multi(stores: list[StoreFn], vc: ExprFn) -> StmtFn:
    """`t1 = t2 = ... = value`: the value is evaluated once and stored into
    each target from left to right."""
    def assign_multi(fr: Frame) -> None:
        v: Any = vc(fr)
        for st in stores:
            st(fr, v)
    return assign_multi


# -- augmented assignment -------------------------------------------------------------


def compile_augassign(comp: Compiler, s: AugAssign) -> StmtFn:
    """`target op= value`: the target is read, combined with the value by
    the in-place operator and stored back; for an attribute or subscript the
    object (and index) are evaluated only once."""
    t: Expression = s.target
    op: str = s.op
    iop: Callable[[Any, Any], Any] = INPLACE_OPS[op]
    vc: ExprFn = comp.expr(s.value)
    if type(t) is Name:
        return augassign_name(comp, t.id, op, iop, vc)
    if type(t) is Attribute:
        return make_iop_attr(comp.expr(t.value), t.attr, iop, vc)
    # The parser only allows Name, Attribute and Subscript targets.
    item: Subscript = cast('Subscript', t)
    return make_iop_item(comp.expr(item.value), comp.expr(item.index), iop, vc)


def augassign_name(comp: Compiler, name: str, op: str, iop: Callable[[Any, Any], Any], vc: ExprFn) -> StmtFn:
    """`name op= value`.  For a local variable the common `+=` and `-=` use
    the operator syntax directly instead of calling the operator function."""
    kind: Signal = comp.resolve(name)[0]
    if kind is LOCAL:
        if op == '+':
            return make_iadd_local(name, vc)
        if op == '-':
            return make_isub_local(name, vc)
        return make_iop_local(name, iop, vc)
    return make_iop_name(load_name(comp, name), store_name(comp, name), iop, vc)


def make_iadd_local(name: str, vc: ExprFn) -> StmtFn:
    """`name += value` for a local variable."""
    def iadd_local(fr: Frame) -> None:
        try:
            v: Any = fr[name]
        except KeyError:
            raise unbound_local(name) from None
        v += vc(fr)
        fr[name] = v
    return iadd_local


def make_isub_local(name: str, vc: ExprFn) -> StmtFn:
    """`name -= value` for a local variable."""
    def isub_local(fr: Frame) -> None:
        try:
            v: Any = fr[name]
        except KeyError:
            raise unbound_local(name) from None
        v -= vc(fr)
        fr[name] = v
    return isub_local


def make_iop_local(name: str, iop: Callable[[Any, Any], Any], vc: ExprFn) -> StmtFn:
    """`name op= value` for a local variable."""
    def iop_local(fr: Frame) -> None:
        try:
            v: Any = fr[name]
        except KeyError:
            raise unbound_local(name) from None
        fr[name] = iop(v, vc(fr))
    return iop_local


def make_iop_name(load: ExprFn, store: StoreFn, iop: Callable[[Any, Any], Any], vc: ExprFn) -> StmtFn:
    """`name op= value` for a global, free or class-level name."""
    def iop_name(fr: Frame) -> None:
        store(fr, iop(load(fr), vc(fr)))
    return iop_name


def make_iop_attr(oc: ExprFn, name: str, iop: Callable[[Any, Any], Any], vc: ExprFn) -> StmtFn:
    """`obj.name op= value`."""
    def iop_attr(fr: Frame) -> None:
        o: Any = oc(fr)
        setattr_any(o, name, iop(getattr_any(o, name), vc(fr)))
    return iop_attr


def make_iop_item(oc: ExprFn, ic: ExprFn, iop: Callable[[Any, Any], Any], vc: ExprFn) -> StmtFn:
    """`obj[index] op= value`."""
    def iop_item(fr: Frame) -> None:
        o: Any = oc(fr)
        i: Any = ic(fr)
        o[i] = iop(o[i], vc(fr))
    return iop_item


# -- imports -----------------------------------------------------------------------------


def compile_import(comp: Compiler, s: Import) -> StmtFn:
    """`import a.b.c` binds the top-level module `a`; `import a.b.c as d`
    binds the submodule a.b.c itself."""
    g: Frame = comp.g
    specs: list[tuple[str, bool, StoreFn]] = []
    for dotted, asname in s.names:
        if asname is not None:
            specs.append((dotted, True, store_name(comp, asname)))
        else:
            specs.append((dotted, False, store_name(comp, dotted.split('.')[0])))

    def import_(fr: Frame) -> None:
        for dotted, has_as, store in specs:
            m: Any = import_module(dotted, g, 0)
            if has_as:
                store(fr, m)
            else:
                store(fr, module_for(dotted.split('.')[0]))
    return import_


def compile_importfrom(comp: Compiler, s: ImportFrom) -> StmtFn:
    """`from module import a, b as c` and `from module import *`."""
    g: Frame = comp.g
    modname: str = s.module or ''
    specs: list[tuple[str, StoreFn]] = []
    star: bool = False
    for name, asname in s.names:
        if name == '*':
            star = True
        else:
            specs.append((name, store_name(comp, asname or name)))
    if star:
        return make_import_star(g, modname, s.level)
    return make_import_names(g, modname, s.level, specs)


def make_import_star(g: Frame, modname: str, level: int) -> StmtFn:
    """`from module import *`: copy the names listed in the module's
    __all__, or else all its names not starting with an underscore."""
    def import_star(fr: Frame) -> None:
        m: Any = import_module(modname, g, level)
        d: dict[str, Any] = module_dict(m)
        names: Any = d.get('__all__')
        if names is not None:
            import_all(m, names, g, fr)
            return
        for k in [k for k in d if k[:1] != '_']:
            fr[k] = d[k]
    return import_star


def import_all(m: Any, names: Any, g: Frame, fr: Frame) -> None:
    """Bind in fr the names listed in the __all__ of module m (`from m
    import *`).  As in CPython, a name that is not an attribute of a package
    is imported as its submodule first, and a missing one is an
    AttributeError."""
    d: dict[str, Any] = module_dict(m)
    for k in names:
        if type(k) is not str:
            raise TypeError(f'Item in {m.__name__}.__all__ must be str, not {type_name(k)}')
        if k not in d and hasattr(m, '__path__'):
            try:
                import_module(m.__name__ + '.' + k, g, 0)
            except ModuleNotFoundError:
                pass
        fr[k] = getattr_any(m, k)


def make_import_names(g: Frame, modname: str, level: int, specs: list[tuple[str, StoreFn]]) -> StmtFn:
    """`from module import name, ...`: each name is an attribute of the
    module or, failing that, a submodule of it."""
    def import_names(fr: Frame) -> None:
        m: Any = import_module(modname, g, level)
        for name, store in specs:
            try:
                v: Any = getattr_special(m, name)
            except AttributeError:
                mname: str = getattr(m, '__name__', modname)
                try:
                    v = import_module(mname + '.' + name, g, 0)
                except ImportError:
                    raise cannot_import(m, name, mname) from None
            store(fr, v)
    return import_names


def cannot_import(m: Any, name: str, mname: str) -> ImportError:
    """The error for `from m import name` when m (called mname) has no
    attribute or submodule `name`; like CPython, it shows m's file."""
    where: Any = getattr(m, '__file__', None)
    location: str = f'({where})' if where else '(unknown location)'
    return ImportError(f"cannot import name '{name}' from '{mname}' {location}", name=mname)


# -- if, while and for -------------------------------------------------------------------


def compile_if(comp: Compiler, s: If) -> StmtFn:
    """`if test: body else: orelse` (an `elif` is an `if` in the orelse)."""
    tc: ExprFn = comp.expr(s.test)
    body: StmtFn = block(comp, s.body)
    if not s.orelse:
        return make_if(comp, tc, body, body_line(comp, s.body, s.line))
    orelse: StmtFn = block(comp, s.orelse)
    return make_if_else(comp, tc, body, orelse, body_line(comp, s.body, s.line))


def make_if(comp: Compiler, tc: ExprFn, body: StmtFn, line: int) -> StmtFn:
    """`if test: body` with no else branch."""
    name: str = comp.code_name
    filename: str = comp.filename

    def if_(fr: Frame) -> Signal | None:
        try:
            if tc(fr):
                return body(fr)
        except BaseException as e:
            annotate(e, fr, line, name, filename)
            raise
        return None
    return if_


def make_if_else(comp: Compiler, tc: ExprFn, body: StmtFn, orelse: StmtFn, line: int) -> StmtFn:
    """`if test: body else: orelse`."""
    name: str = comp.code_name
    filename: str = comp.filename

    def if_else(fr: Frame) -> Signal | None:
        try:
            if tc(fr):
                return body(fr)
            return orelse(fr)
        except BaseException as e:
            annotate(e, fr, line, name, filename)
            raise
    return if_else


def compile_while(comp: Compiler, s: While) -> StmtFn:
    """`while test: body else: orelse`.

    The body's BREAK and CONTINUE signals are consumed here; RETURN is
    passed on.  The else branch runs only if the loop was not broken."""
    tc: ExprFn = comp.expr(s.test)
    body: StmtFn = block(comp, s.body)
    orelse: StmtFn | None = block(comp, s.orelse) if s.orelse else None
    line: int = body_line(comp, s.body, s.line)
    name: str = comp.code_name
    filename: str = comp.filename

    def while_(fr: Frame) -> Signal | None:
        try:
            while tc(fr):
                r: Signal | None = body(fr)
                if r is not None:
                    if r is BREAK:
                        return None
                    if r is CONTINUE:
                        continue
                    return r
            if orelse is not None:
                return orelse(fr)
        except BaseException as e:
            annotate(e, fr, line, name, filename)
            raise
        return None
    return while_


def compile_for(comp: Compiler, s: For) -> StmtFn:
    """`for target in iterable: body else: orelse`.

    Loop signals are handled as in compile_while.  A loop variable that is
    a plain local name is stored directly into the frame."""
    if s.is_async:
        raise syntax_error("'async for' outside async function", comp.filename, s.line)
    itc: ExprFn = comp.expr(s.iter)
    body: StmtFn = block(comp, s.body)
    orelse: StmtFn | None = block(comp, s.orelse) if s.orelse else None
    line: int = body_line(comp, s.body, s.line)
    var: str | None = comp.local_name(s.target)
    if var is not None:
        return make_for_local(comp, itc, var, body, orelse, line)
    return make_for(comp, itc, target(comp, s.target), body, orelse, line)


def make_for_local(comp: Compiler, itc: ExprFn, var: str, body: StmtFn, orelse: StmtFn | None,
                   line: int) -> StmtFn:
    """A for loop whose target is the local variable var."""
    name: str = comp.code_name
    filename: str = comp.filename

    def for_local(fr: Frame) -> Signal | None:
        try:
            for x in itc(fr):
                fr[var] = x
                r: Signal | None = body(fr)
                if r is not None:
                    if r is BREAK:
                        return None
                    if r is CONTINUE:
                        continue
                    return r
            if orelse is not None:
                return orelse(fr)
        except BaseException as e:
            annotate(e, fr, line, name, filename)
            raise
        return None
    return for_local


def make_for(comp: Compiler, itc: ExprFn, store: StoreFn, body: StmtFn, orelse: StmtFn | None,
             line: int) -> StmtFn:
    """A for loop with any other target, stored through a store function."""
    name: str = comp.code_name
    filename: str = comp.filename

    def for_(fr: Frame) -> Signal | None:
        try:
            for x in itc(fr):
                store(fr, x)
                r: Signal | None = body(fr)
                if r is not None:
                    if r is BREAK:
                        return None
                    if r is CONTINUE:
                        continue
                    return r
            if orelse is not None:
                return orelse(fr)
        except BaseException as e:
            annotate(e, fr, line, name, filename)
            raise
        return None
    return for_


# -- try ------------------------------------------------------------------------------


def handlers(comp: Compiler, s: Try,
             compile_body: Callable[[Compiler, list[Statement]], Callable[[Frame], Any]]) -> list[Handler]:
    """Compile the `except` clauses of s, compiling each handler body with
    compile_body (block, or gen_block in generator mode)."""
    hs: list[Handler] = []
    for h in s.handlers:
        tc: ExprFn | None = comp.expr(h.type) if h.type is not None else None
        store: StoreFn | None = None
        unbind: Callable[[Frame], None] = noop  # only called when there is a name to unbind
        if h.name is not None:
            store = store_name(comp, h.name)
            unbind = unbind_name(comp, h.name)
        hs.append((tc, store, unbind, compile_body(comp, h.body)))
    return hs


def compile_try(comp: Compiler, s: Try) -> StmtFn:
    """`try: body except ...: handler else: orelse finally: final`.

    The body with its except and else clauses becomes one closure, which a
    `finally` clause then wraps in another."""
    body: StmtFn = block(comp, s.body)
    where: Where | None = single_statement_where(comp, s.body)
    hs: list[Handler] = handlers(comp, s, handler_compiler(None if s.star else where))
    orelse: StmtFn | None = block(comp, s.orelse) if s.orelse else None
    final: StmtFn | None = block(comp, s.finalbody) if s.finalbody else None
    if s.star:
        attempt: StmtFn = make_try_star(body, hs, orelse, where)
    else:
        attempt = make_try_except(body, hs, orelse) if hs else body
    if final is None:
        return attempt
    return make_try_finally(attempt, final, where)


# Tracebacks through try statements.  A body of several statements is a
# run_block, which records the line of the statement that raised, but a
# body of a single statement is that statement's closure, so the try
# statement records the line itself (`where`), off the normal path: an
# except clause records it for the exception it handles, and a finally
# clause for the exception passing through it.  (The try_except closure
# itself is left alone: it runs for every try statement of the interpreter
# itself, which is hot when boros runs boros.)

def single_statement_where(comp: Compiler, stmts: list[Statement]) -> Where | None:
    """Where the statement of a try body consisting of a single statement
    is, or None if the body has several (or no) statements."""
    real: list[Statement] = real_statements(stmts)
    if len(real) != 1:
        return None
    return (real[0].line, comp.code_name, comp.filename)


def handler_compiler(where: Where | None) -> Callable[[Compiler, list[Statement]], StmtFn]:
    """The compile function for the except clauses of a try statement whose
    body is the single statement at `where` (or None): see make_run_handler."""
    def compile_handler(comp: Compiler, stmts: list[Statement]) -> StmtFn:
        real: list[Statement] = real_statements(stmts)
        if not real:
            return noop
        return make_run_handler(comp, [comp.stmt(s) for s in real], [s.line for s in real], where)
    return compile_handler


def make_run_handler(comp: Compiler, cs: list[StmtFn], lines: list[int], where: Where | None) -> StmtFn:
    """The body of an except clause: run_block, which also records the line
    of a single failing statement, after recording `where` for the exception
    being handled.  It runs only after an exception, so this costs nothing
    on the normal path."""
    name: str = comp.code_name
    filename: str = comp.filename
    first: StmtFn = cs[0]

    def run_handler(fr: Frame) -> Signal | None:
        if where is not None:
            e: BaseException | None = sys.exc_info()[1]
            if e is not None:
                annotate(e, fr, where[0], where[1], where[2])
        s: StmtFn = first
        try:
            for s in cs:
                r: Signal | None = s(fr)
                if r is not None:
                    return r
        except BaseException as x:
            annotate(x, fr, lines[cs.index(s)], name, filename)
            raise
        return None
    return run_handler


def make_try_except(body: StmtFn, hs: list[Handler], orelse: StmtFn | None) -> StmtFn:
    """Run body; if it raises, run the first handler whose exception type
    matches (re-raising if none does), else run orelse.

    As in Python, the name bound by `except E as name` is removed again when
    the handler finishes."""
    def try_except(fr: Frame) -> Signal | None:
        try:
            r: Signal | None = body(fr)
        except BaseException as e:
            v: Any = exc_value(e)
            for tc, store, unbind, hb in hs:
                if tc is None or exc_matches(v, tc(fr)):
                    break
            else:
                raise
            if store is None:
                return hb(fr)
            store(fr, v)
            try:
                return hb(fr)
            finally:
                unbind(fr)
        if r is not None:
            return r
        if orelse is not None:
            return orelse(fr)
        return None
    return try_except


def make_try_star(body: StmtFn, hs: list[Handler], orelse: StmtFn | None, where: Where | None) -> StmtFn:
    """Run body; if it raises, run its except* clauses (see
    run_star_handlers) and raise what they leave unhandled, else run orelse."""
    def try_star(fr: Frame) -> Signal | None:
        x: BaseException | None = None
        try:
            r: Signal | None = body(fr)
        except BaseException as e:
            if where is not None:
                annotate(e, fr, where[0], where[1], where[2])
            x = run_star_handlers(fr, e, hs)
            if x is e:
                raise
        else:
            if r is not None:
                return r
            if orelse is not None:
                return orelse(fr)
            return None
        if x is not None:
            # raised outside the handler, so that it does not get e as context
            raise x
        return None
    return try_star


def run_star_handlers(fr: Frame, e: BaseException, hs: list[Handler]) -> BaseException | None:
    """Run the except* clauses hs for host exception e, each on the part of
    e that the clauses before it did not match.  Returns the exception left
    to raise (see runtime.exceptions.star_result), or None."""
    raised: list[tuple[BaseException, BaseException]] = []
    rest: BaseException | None = e
    for tc, store, unbind, hb in hs:
        match, rest = star_match(rest, tc(fr) if tc is not None else BaseException)
        if match is not None:
            x: BaseException | None = run_star_handler(fr, match, store, unbind, hb)
            if x is not None:
                raised.append((match, x))
    return star_result(e, raised, rest)


def run_star_handler(fr: Frame, match: BaseException, store: StoreFn | None, unbind: Callable[[Frame], None],
                     hb: StmtFn) -> BaseException | None:
    """Run the body hb of an except* clause with `match` (the matching part
    of the exception) as the exception being handled and bound to the
    clause's name; returns the exception the body raised, if any."""
    ctx: BaseException | None = match.__context__
    body: CatchAll = CatchAll()
    try:
        raise match
    except BaseExceptionGroup:
        match.__context__ = ctx
        if store is not None:
            store(fr, exc_value(match))
        with body:
            try:
                hb(fr)
            finally:
                unbind(fr)
    return body.caught


def make_try_finally(attempt: StmtFn, final: StmtFn, where: Where | None = None) -> StmtFn:
    """Run attempt, then final however attempt finishes.  If final itself
    ends with a signal (a break, continue or return in the finally clause),
    that signal wins, even over an exception raised by attempt.  An
    exception from attempt is recorded at `where` in the traceback."""
    def try_finally(fr: Frame) -> Signal | None:
        try:
            r: Signal | None = attempt(fr)
        except BaseException as e:
            if where is not None:
                annotate(e, fr, where[0], where[1], where[2])
            f: Signal | None = final(fr)
            if f is not None:
                return f
            raise
        f = final(fr)
        if f is not None:
            return f
        return r
    return try_finally


# -- with --------------------------------------------------------------------------------


def compile_with(comp: Compiler, s: With) -> StmtFn:
    """`with a as x, b as y: body` is compiled as nested single-item with
    statements, the first item outermost."""
    if s.is_async:
        raise syntax_error("'async with' outside async function", comp.filename, s.line)
    inner: StmtFn = block(comp, s.body)
    for item in reversed(s.items):
        inner = compile_with_item(comp, item, inner)
    return inner


def compile_with_item(comp: Compiler, item: WithItem, inner: StmtFn) -> StmtFn:
    """One context manager around the compiled statement inner.

    __enter__'s result is stored in the `as` target; __exit__ is called
    with the exception if inner raises (a true result suppresses it) and
    with three Nones otherwise.  An interpreted __exit__ gets the
    interpreted exception, a host one the host exception object that
    carries it (host code such as contextlib throws and compares it)."""
    mc: ExprFn = comp.expr(item.expr)
    store: StoreFn | None = target(comp, item.target) if item.target is not None else None

    def with_(fr: Frame) -> Signal | None:
        mgr: Any = mc(fr)
        enter, exit_ = context_methods(mgr)
        v: Any = enter()
        if store is not None:
            store(fr, v)
        try:
            r: Signal | None = inner(fr)
        except BaseException as e:
            ev: Any = exc_value(e)
            if not exit_(exc_type(ev), ev if type(mgr) is Instance else e, e.__traceback__):
                raise
            return None
        exit_(None, None, None)
        return r
    return with_
