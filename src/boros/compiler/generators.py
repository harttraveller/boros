"""Generator mode: compiling code that contains `yield` or `await`.

Ordinary statement closures cannot stop half way and resume later, so the
body of a generator function (or of an async function, whose `await`s
suspend it in the same way) is compiled in *generator mode*: every
statement that contains a yield becomes a host generator function `g(fr)`,
and these are chained with `yield from`.  A host-level `yield` deep inside
then suspends the whole chain at once, and the host generator returned by
the body is the interpreted generator object, so next(), send(), throw()
and close() work unchanged.  The value of compiled code in generator mode is
the return value of its generator: a signal for statements and the value
for expressions.

Statements without a yield are compiled as usual (comp.stmt) and called
directly.  Expressions are handled by *hoisting*: each sub-expression that
contains a yield is evaluated first, in generator mode, into a temporary
slot of the frame, and the rest of the expression or statement is then
compiled as usual, with a Temp node reading that slot in place of the
sub-expression.

Two host rules about generators are worked around with the helpers of
runtime/coroutines.py.  Interpreted code that raises StopIteration inside
the chain raises it as a StopCarrier instead (a StopIteration leaving a
host generator frame would become RuntimeError before the interpreted
generator's own `except` could catch it), and the interpreted yield points
turn a GenClose thrown in back into GeneratorExit.  A body with a try or
with statement that could stop the GeneratorExit of close() at a yield (and
the body of every async generator) is run under coroutines.drive, which
delivers close() as GenClose; any other body runs as a plain chain, which
is faster.  Calls `x.throw(exc)` are compiled to pass the host exception
standing for an interpreted one (see calls.make_exc_mcall).
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from ..lexer import syntax_error
from ..runtime.attributes import delattr_any, getattr_any, setattr_any
from ..runtime.coroutines import STOP_MESSAGES, GenClose, StopCarrier, agen_yield, await_value, carry_stop, drive
from ..runtime.errors import annotate, exc_value
from ..runtime.exceptions import CatchAll, exc_matches, star_match, star_result, to_native_exc
from ..runtime.objects import BREAK, CONTINUE, MISSING, RETURN, Instance
from ..runtime.protocols import (
    aiter_of,
    anext_awaitable,
    async_context_methods,
    await_iter,
    context_methods,
    exc_type,
)
from ..runtime.typechecks import type_name
from ..syntax import (
    COMPOUND,
    Arguments,
    Assert,
    Assign,
    Attribute,
    AugAssign,
    Await,
    BoolOp,
    Break,
    ClassDef,
    Compare,
    Const,
    Continue,
    Delete,
    DictComp,
    DictDisplay,
    Expression,
    ExprStmt,
    For,
    FunctionDef,
    GeneratorExp,
    If,
    IfExp,
    Keyword,
    Lambda,
    List,
    ListComp,
    Match,
    Name,
    NamedExpr,
    Node,
    Raise,
    Return,
    SetComp,
    Starred,
    Subscript,
    Temp,
    Try,
    Tuple,
    While,
    With,
    Yield,
    YieldFrom,
)
from .names import load_name, store_name
from .operators import COMPARE_FUNCS, INPLACE_OPS
from .patterns import pattern
from .statements import handlers, noop, real_statements
from .targets import del_target, target, unpack

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable

    from ..core_types import ExprFn, Frame, GenFn, StmtFn, StoreFn
    from ..runtime.objects import Signal
    from ..syntax import Comprehension, Scope, Statement, WithItem
    from .compiler import Compiler
    from .patterns import PatternFn
    from .statements import Handler

    Hoisted = list[tuple[str, GenFn]]
    """Hoisted sub-expressions: (temporary key, generator computing its value),
    to be evaluated in order before the code that reads the temporaries."""

    GenStoreFn = Callable[[Frame, Any], Generator[Any, Any, Any]]
    """An assignment target in generator mode: a generator function that
    evaluates the target's sub-expressions and stores the value."""

    AnyComp = ListComp | SetComp | DictComp | GeneratorExp
    """Any comprehension node."""


# -- finding yields -------------------------------------------------------------------


def contains_yield(n: Node) -> bool:
    """Does n contain `yield`, `yield from` or `await` (or `async for` or
    `async with`) outside of any nested scope?  Of a nested function,
    lambda, class or comprehension only the parts evaluated in the current
    scope (decorators, defaults, bases, the first iterable) are searched."""
    t: type[Node] = type(n)
    if t is Yield or t is YieldFrom or t is Await:
        return True
    if (type(n) is For or type(n) is With) and n.is_async:
        return True
    in_scope: Callable[[Any], bool] | None = SCOPE_BOUNDARIES.get(t)
    if in_scope is not None:
        return in_scope(n)
    return children_contain_yield(n)


def children_contain_yield(n: Node) -> bool:
    """Does any child node of n contain a yield?"""
    for f in type(n)._fields:
        v: Any = getattr(n, f)
        if isinstance(v, Node):
            if contains_yield(v):
                return True
        elif type(v) is list:
            for x in v:
                if isinstance(x, Node) and contains_yield(x):
                    return True
    return False


def any_yield(nodes: Iterable[Node]) -> bool:
    """Does any of nodes contain a yield?"""
    for x in nodes:
        if contains_yield(x):
            return True
    return False


def defaults_yield(args: Arguments) -> bool:
    """Does a default value of a parameter list contain a yield?"""
    return any_yield(args.defaults) or any_yield([d for d in args.kw_defaults if d is not None])


def lambda_yields(n: Lambda) -> bool:
    """Only a lambda's defaults are evaluated in the enclosing scope."""
    return defaults_yield(n.args)


def function_yields(n: FunctionDef) -> bool:
    """Only a function's decorators and defaults are evaluated in the enclosing scope."""
    return any_yield(n.decorators) or defaults_yield(n.args)


def class_yields(n: ClassDef) -> bool:
    """Only a class's decorators, bases and keywords are evaluated in the enclosing scope."""
    return any_yield(n.decorators) or any_yield(n.bases) or any_yield(n.keywords)


def comprehension_yields(n: ListComp | SetComp | DictComp | GeneratorExp) -> bool:
    """Only a comprehension's first iterable is evaluated in the enclosing scope."""
    return contains_yield(n.gens[0].iter)


def list_comprehension_yields(n: ListComp | SetComp | DictComp) -> bool:
    """A list, set or dict comprehension containing `async for` or `await`
    runs in the enclosing coroutine, so it suspends it like an await."""
    return contains_yield(n.gens[0].iter) or is_async_comp(n)


SCOPE_BOUNDARIES: dict[type, Callable[[Any], bool]] = {
    Lambda: lambda_yields, FunctionDef: function_yields, ClassDef: class_yields,
    ListComp: list_comprehension_yields, SetComp: list_comprehension_yields, DictComp: list_comprehension_yields,
    GeneratorExp: comprehension_yields,
}


def is_async_comp(n: AnyComp) -> bool:
    """Is n an asynchronous comprehension: does it contain `async for`, or
    an await (or yield) outside its first iterable, which belongs to the
    enclosing scope?"""
    for i, gen in enumerate(n.gens):
        if gen.is_async or any_yield(gen.ifs) or (i > 0 and contains_yield(gen.iter)):
            return True
    if isinstance(n, DictComp):
        return contains_yield(n.key) or contains_yield(n.value)
    return contains_yield(n.elt)


def find_yield(n: Node) -> bool:
    """Does n contain `yield` or `yield from` (not await) outside of nested
    functions and classes?"""
    t: type[Node] = type(n)
    if t is Yield or t is YieldFrom:
        return True
    if t is Lambda or t is FunctionDef or t is ClassDef:
        return False
    return any_child(n, find_yield)


def any_child(n: Node, pred: Callable[[Node], bool]) -> bool:
    """Does pred hold for a child node of n?"""
    for f in type(n)._fields:
        v: Any = getattr(n, f)
        if isinstance(v, Node):
            if pred(v):
                return True
        elif type(v) is list:
            for x in v:
                if isinstance(x, Node) and pred(x):
                    return True
    return False


COMP_KIND_NAMES: dict[str, str] = {'list': 'list comprehension', 'set': 'set comprehension',
                                   'dict': 'dict comprehension', 'gen': 'generator expression'}
"""How the compile-time errors of each kind of comprehension name it."""


def check_comp_yield(comp: Compiler, n: AnyComp, kind: str) -> None:
    """A yield in the part of a comprehension that runs in its own scope
    (all but the first iterable) is a SyntaxError."""
    parts: list[Node] = [n.key, n.value] if isinstance(n, DictComp) else [n.elt]
    for i, gen in enumerate(n.gens):
        if i > 0:
            parts.append(gen.iter)
        parts.extend(gen.ifs)
    for x in parts:
        if find_yield(x):
            raise SyntaxError(f"'yield' inside {COMP_KIND_NAMES[kind]} ({comp.filename}, line {n.line})")


def function_scope(comp: Compiler) -> Scope:
    """The innermost scope that is not a comprehension's."""
    for s in reversed(comp.stack):
        if s.kind != 'comp':
            return s
    return comp.stack[0]


def in_async_function(comp: Compiler) -> bool:
    """Is the code being compiled (directly or in comprehensions) in the
    body of an `async def`?"""
    s: Scope = function_scope(comp)
    return s.kind == 'function' and s.is_async


def clone(n: Node) -> Any:
    """A shallow copy of syntax node n (of the same type as n)."""
    c: Any = Node.__new__(type(n))
    c.line = n.line
    for f in n._fields:
        setattr(c, f, getattr(n, f))
    return c


# -- statement lists ------------------------------------------------------------------


def gen_body(comp: Compiler, stmts: list[Statement]) -> GenFn:
    """Compile the body of a generator (or async) function.  The returned
    function creates the host generator; its return value (the value of
    StopIteration) is the function's return value."""
    blk: GenFn = gen_block(comp, stmts)
    scope: Scope = comp.stack[-1]
    if scope.is_async and scope.has_yield:
        # an async generator's aclose() needs drive (its cleanup may await)
        check_async_gen_returns(comp, stmts)
        return make_driven_body(blk, 3)
    kind: int = 2 if scope.is_async else 0
    for s in stmts:
        if needs_drive(s):
            return make_driven_body(blk, kind)
    return make_plain_body(blk, kind)


def make_plain_body(blk: GenFn, kind: int) -> GenFn:
    """A generator (kind 0) or coroutine (2) body run as a plain chain of
    host generators."""
    def run_gen(fr: Frame) -> Generator[Any, Any, Any]:
        try:
            r: Signal | None = yield from blk(fr)
        except StopCarrier as c:
            raise RuntimeError(STOP_MESSAGES[kind]) from c.exc
        if r is RETURN:
            return fr['.rv']
        return None
    return run_gen


def make_driven_body(blk: GenFn, kind: int) -> GenFn:
    """A generator (kind 0), coroutine (2) or async generator (3) body run
    under coroutines.drive."""
    def run_driven(fr: Frame) -> Generator[Any, Any, Any]:
        return drive(blk(fr), fr, kind)
    return run_driven


def needs_drive(n: Node) -> bool:
    """Must a generator whose body contains n run under coroutines.drive?
    It must when the GeneratorExit of close() at a yield could be stopped by
    a try or with statement: only drive delivers close() to the innermost
    yield like any other exception.  (Other exceptions thrown in reach it in
    a plain chain too.)"""
    if isinstance(n, Try):
        return try_needs_drive(n)
    t: type[Node] = type(n)
    if t is With or t in SCOPE_BOUNDARIES:
        return contains_yield(n)
    return any_child(n, needs_drive)


def try_needs_drive(s: Try) -> bool:
    """Could try statement s stop a GeneratorExit raised at a yield inside
    it?  A handler stops it unless its type cannot match GeneratorExit or it
    always raises; a finally clause does when it returns, breaks or
    continues."""
    if any_yield(s.body):
        for h in s.handlers:
            if may_catch_exit(h.type) and not always_raises(h.body):
                return True
    if any(has_jump(x) for x in s.finalbody) and contains_yield(s):
        return True
    return any_child(s, needs_drive)


NARROW_EXCEPTIONS: dict[str, int] = {k: 1 for k, v in vars(builtins).items()
                                     if isinstance(v, type) and issubclass(v, Exception)}
"""The names of the builtin exception classes derived from Exception, which
an except clause can name without catching GeneratorExit (used as a set)."""


def may_catch_exit(typ: Expression | None) -> bool:
    """Could `except typ` catch GeneratorExit?  Only names of builtin
    Exception subclasses (or tuples of them) certainly do not."""
    if type(typ) is Name:
        return typ.id not in NARROW_EXCEPTIONS
    if type(typ) is Tuple:
        return any(may_catch_exit(e) for e in typ.elts)
    return True


def always_raises(body: list[Statement]) -> bool:
    """Does a handler body of simple statements end with `raise`?"""
    real: list[Statement] = real_statements(body)
    for x in real:
        t: type[Statement] = type(x)
        if t in COMPOUND or t is Return or t is Break or t is Continue:
            return False
    return bool(real) and type(real[-1]) is Raise


def has_jump(n: Node) -> bool:
    """Does n contain return, break or continue (outside nested functions)?"""
    t: type[Node] = type(n)
    if t is Return or t is Break or t is Continue:
        return True
    if t is FunctionDef or t is ClassDef or t is Lambda:
        return False
    return any_child(n, has_jump)


def check_async_gen_returns(comp: Compiler, stmts: Iterable[Node]) -> None:
    """`return value` is a SyntaxError in an async generator (nested
    functions and classes are not searched)."""
    for s in stmts:
        t: type[Node] = type(s)
        if t is FunctionDef or t is ClassDef:
            continue
        if isinstance(s, Return) and s.value is not None:
            raise SyntaxError(f"'return' with value in async generator ({comp.filename}, line {s.line})")
        for f in t._fields:
            v: Any = getattr(s, f)
            if type(v) is list:
                check_async_gen_returns(comp, [x for x in v if isinstance(x, Node)])


def gen_block(comp: Compiler, stmts: list[Statement]) -> GenFn:
    """Compile a statement list in generator mode: statements containing a
    yield are compiled with gen_stmt and run with `yield from`, the others
    are compiled normally and called directly.  As in block(), the first
    signal ends the list and the line of a failing statement is recorded."""
    # Each item is (is generator code, compiled statement (a GenFn or a StmtFn), line).
    items: list[tuple[bool, Callable[[Frame], Any], int]] = []
    for s in real_statements(stmts):
        if contains_yield(s):
            items.append((True, gen_stmt(comp, s), s.line))
        else:
            items.append((False, comp.stmt(s), s.line))
    name: str = comp.code_name
    filename: str = comp.filename

    def run_gblock(fr: Frame) -> Generator[Any, Any, Any]:
        for is_gen, c, line in items:
            try:
                if is_gen:
                    r: Signal | None = yield from c(fr)
                else:
                    r = c(fr)
            except StopIteration as e:
                annotate(e, fr, line, name, filename)
                raise carry_stop(e) from None
            except StopCarrier as e:
                annotate(e.exc, fr, line, name, filename)
                raise
            except BaseException as e:
                annotate(e, fr, line, name, filename)
                raise
            if r is not None:
                return r
        return None
    return run_gblock


def gen_stmt(comp: Compiler, s: Statement) -> GenFn:
    """Compile a statement that contains a yield."""
    compile_stmt: Callable[[Compiler, Any], GenFn] | None = GEN_STMT_COMPILERS.get(type(s))
    if compile_stmt is None:
        return gen_simple_stmt(comp, s)
    return compile_stmt(comp, s)


# -- hoisting -----------------------------------------------------------------------------


def hoist(comp: Compiler, n: Expression) -> tuple[Hoisted, Expression]:
    """Prepare expression n for use by normally compiled code: returns
    (pre, new), where pre lists the generators to evaluate first and new is
    the expression to compile instead of n.  An expression containing a
    yield is replaced as a whole by a temporary."""
    if not contains_yield(n):
        return [], n
    key: str = comp.new_temp()
    return [(key, gen_expr(comp, n))], Temp(n.line, key)


def hoist_statement(comp: Compiler, s: Statement) -> tuple[Hoisted, Statement]:
    """A copy of simple statement s in which each expression child (or item
    of a list of children) that contains a yield is hoisted."""
    new: Statement = clone(s)
    pre: Hoisted = []
    for f in s._fields:
        v: Any = getattr(s, f)
        if isinstance(v, Expression):
            p, nv = hoist(comp, v)
            pre.extend(p)
            setattr(new, f, nv)
        elif type(v) is Arguments:
            setattr(new, f, hoist_arguments(comp, v, pre))
        elif type(v) is list:
            nl: list[Any] = []
            for x in v:
                if isinstance(x, Expression):
                    p, nx = hoist(comp, x)
                    pre.extend(p)
                    nl.append(nx)
                elif type(x) is Keyword and contains_yield(x):
                    nl.append(hoist_child(comp, x, pre))
                else:
                    nl.append(x)
            setattr(new, f, nl)
    return pre, new


def hoist_arguments(comp: Compiler, a: Arguments, pre: Hoisted) -> Arguments:
    """A copy of the parameter list of a def or lambda whose default values
    are hoisted (they are evaluated where the function is defined)."""
    if not defaults_yield(a):
        return a
    new: Arguments = clone(a)
    new.defaults = [hoist_expr(comp, d, pre) for d in a.defaults]
    new.kw_defaults = [hoist_expr(comp, d, pre) if d is not None else None for d in a.kw_defaults]
    return new


def hoist_child(comp: Compiler, x: Node, pre: Hoisted) -> Node:
    """Hoist a child node of an expression, appending to pre (used by
    gen_generic, which evaluates every child in order)."""
    if type(x) is Keyword:
        new: Keyword = clone(x)
        new.value = hoist_expr(comp, x.value, pre)
        return new
    if isinstance(x, Expression):
        return hoist_expr(comp, x, pre)
    if contains_yield(x):
        raise syntax_error('yield is not supported in this position', comp.filename, x.line)
    return x


def hoist_expr(comp: Compiler, x: Expression, pre: Hoisted) -> Expression:
    """Hoist expression x into a temporary, appending its generator to pre.
    Constants are left in place, and `*x` hoists x but keeps the star."""
    if type(x) is Starred:
        new: Starred = clone(x)
        new.value = hoist_expr(comp, x.value, pre)
        return new
    if type(x) is Const:
        return x
    key: str = comp.new_temp()
    pre.append((key, gen_expr(comp, x)))
    return Temp(x.line, key)


# -- statements -------------------------------------------------------------------------


def gen_simple_stmt(comp: Compiler, s: Statement) -> GenFn:
    """A simple statement containing a yield: evaluate the hoisted
    sub-expressions, then run the normally compiled rest of the statement."""
    pre, new = hoist_statement(comp, s)
    c: StmtFn = noop
    # An expression statement whose whole value was hoisted (such as a bare
    # `yield x`) has nothing left to do.
    if not (type(new) is ExprStmt and type(new.value) is Temp):
        c = comp.stmt(new)

    def run_simple(fr: Frame) -> Generator[Any, Any, Any]:
        for key, ge in pre:
            fr[key] = yield from ge(fr)
        try:
            return c(fr)
        except StopIteration as e:
            raise carry_stop(e) from None
    return run_simple


def gen_if_stmt(comp: Compiler, s: If) -> GenFn:
    """`if` in generator mode."""
    pre, test = hoist(comp, s.test)
    tc: ExprFn = comp.expr(test)
    body: GenFn = gen_block(comp, s.body)
    orelse: GenFn = gen_block(comp, s.orelse)

    def gen_if(fr: Frame) -> Generator[Any, Any, Any]:
        for key, ge in pre:
            fr[key] = yield from ge(fr)
        try:
            t: Any = tc(fr)
        except StopIteration as e:
            raise carry_stop(e) from None
        if t:
            r: Signal | None = yield from body(fr)
        else:
            r = yield from orelse(fr)
        return r
    return gen_if


def gen_while_stmt(comp: Compiler, s: While) -> GenFn:
    """`while` in generator mode; a hoisted test is re-evaluated on every
    iteration."""
    pre, test = hoist(comp, s.test)
    tc: ExprFn = comp.expr(test)
    body: GenFn = gen_block(comp, s.body)
    if type(test) is Const and test.value:
        return make_gen_forever(body)
    orelse: GenFn | None = gen_block(comp, s.orelse) if s.orelse else None
    return make_gen_while(pre, tc, body, orelse)


def make_gen_while(pre: Hoisted, tc: ExprFn, body: GenFn, orelse: GenFn | None) -> GenFn:
    """A while loop in generator mode."""
    def gen_while(fr: Frame) -> Generator[Any, Any, Any]:
        while True:
            for key, ge in pre:
                fr[key] = yield from ge(fr)
            try:
                t: Any = tc(fr)
            except StopIteration as e:
                raise carry_stop(e) from None
            if not t:
                break
            r: Signal | None = yield from body(fr)
            if r is not None:
                if r is BREAK:
                    return None
                if r is CONTINUE:
                    continue
                return r
        if orelse is not None:
            r = yield from orelse(fr)
            return r
        return None
    return gen_while


def make_gen_forever(body: GenFn) -> GenFn:
    """`while True:` in generator mode (its else clause cannot run)."""
    def gen_forever(fr: Frame) -> Generator[Any, Any, Any]:
        while True:
            r: Signal | None = yield from body(fr)
            if r is not None:
                if r is BREAK:
                    return None
                if r is not CONTINUE:
                    return r
    return gen_forever


def gen_for_stmt(comp: Compiler, s: For) -> GenFn:
    """`for` (or `async for`) in generator mode."""
    pre, itn = hoist(comp, s.iter)
    itc: ExprFn = comp.expr(itn)
    store: StoreFn = target(comp, s.target)
    body: GenFn = gen_block(comp, s.body)
    orelse: GenFn | None = gen_block(comp, s.orelse) if s.orelse else None
    if s.is_async:
        check_async(comp, "'async for'", s.line)
        return make_gen_async_for(pre, itc, store, body, orelse)
    return make_gen_for(pre, itc, store, body, orelse)


def make_gen_for(pre: Hoisted, itc: ExprFn, store: StoreFn, body: GenFn, orelse: GenFn | None) -> GenFn:
    """A for loop in generator mode."""
    def gen_for(fr: Frame) -> Generator[Any, Any, Any]:
        for key, ge in pre:
            fr[key] = yield from ge(fr)
        try:
            xs: Iterable[Any] = iter(itc(fr))
        except StopIteration as e:
            raise carry_stop(e) from None
        for x in xs:
            store(fr, x)
            r: Signal | None = yield from body(fr)
            if r is not None:
                if r is BREAK:
                    return None
                if r is CONTINUE:
                    continue
                return r
        if orelse is not None:
            r = yield from orelse(fr)
            return r
        return None
    return gen_for


def make_gen_async_for(pre: Hoisted, itc: ExprFn, store: StoreFn, body: GenFn, orelse: GenFn | None) -> GenFn:
    """`async for`: items come from awaiting the iterator's __anext__
    until it raises StopAsyncIteration."""
    def gen_async_for(fr: Frame) -> Generator[Any, Any, Any]:
        for key, ge in pre:
            fr[key] = yield from ge(fr)
        it: Any = aiter_of(itc(fr))
        while True:
            try:
                x: Any = yield from await_value(anext_awaitable(it))
            except StopAsyncIteration:
                break
            store(fr, x)
            r: Signal | None = yield from body(fr)
            if r is not None:
                if r is BREAK:
                    return None
                if r is CONTINUE:
                    continue
                return r
        if orelse is not None:
            r = yield from orelse(fr)
            return r
        return None
    return gen_async_for


def check_async(comp: Compiler, what: str, line: int) -> None:
    """`async for`, `async with` and asynchronous comprehensions (what) are
    a SyntaxError outside an `async def`."""
    if not in_async_function(comp):
        raise SyntaxError(f'{what} outside async function ({comp.filename}, line {line})')


def gen_try_stmt(comp: Compiler, s: Try) -> GenFn:
    """`try` in generator mode, structured as in statements.compile_try."""
    if any_yield([h.type for h in s.handlers if h.type is not None]):
        return gen_try_yield_types(comp, s)
    body: GenFn = gen_block(comp, s.body)
    hs: list[Handler] = handlers(comp, s, gen_block)
    orelse: GenFn | None = gen_block(comp, s.orelse) if s.orelse else None
    final: GenFn | None = gen_block(comp, s.finalbody) if s.finalbody else None
    if s.star:
        attempt: GenFn = make_gen_try_star(body, hs, orelse)
    else:
        attempt = make_gen_try_except(body, hs, orelse) if hs else body
    if final is None:
        return attempt
    return make_gen_try_finally(attempt, final)


def make_gen_try_except(body: GenFn, hs: list[Handler], orelse: GenFn | None) -> GenFn:
    """Run body; if it raises, run the first matching handler (re-raising
    if none matches), else run orelse."""
    def gen_try_except(fr: Frame) -> Generator[Any, Any, Any]:
        try:
            r: Signal | None = yield from body(fr)
        except BaseException as e:
            v: Any = exc_value(e)
            for tc, store, unbind, hb in hs:
                if tc is None or exc_matches(v, tc(fr)):
                    break
            else:
                raise
            if store is None:
                r = yield from hb(fr)
                return r
            store(fr, v)
            try:
                r = yield from hb(fr)
            finally:
                unbind(fr)
            return r
        if r is not None:
            return r
        if orelse is not None:
            r = yield from orelse(fr)
            return r
        return None
    return gen_try_except


def make_gen_try_star(body: GenFn, hs: list[Handler], orelse: GenFn | None) -> GenFn:
    """try with except* clauses in generator mode (see statements.make_try_star)."""
    def gen_try_star(fr: Frame) -> Generator[Any, Any, Any]:
        x: BaseException | None = None
        try:
            r: Signal | None = yield from body(fr)
        except BaseException as e:
            x = yield from gen_star_handlers(fr, e, hs)
            if x is e:
                raise
        else:
            if r is not None:
                return r
            if orelse is not None:
                r = yield from orelse(fr)
                return r
            return None
        if x is not None:
            raise x
        return None
    return gen_try_star


def gen_star_handlers(fr: Frame, e: BaseException, hs: list[Handler]) -> Generator[Any, Any, BaseException | None]:
    """statements.run_star_handlers in generator mode."""
    raised: list[tuple[BaseException, BaseException]] = []
    rest: BaseException | None = e
    for tc, store, unbind, hb in hs:
        match, rest = star_match(rest, tc(fr) if tc is not None else BaseException)
        if match is not None:
            x: BaseException | None = yield from gen_star_handler(fr, match, store, unbind, hb)
            if x is not None:
                raised.append((match, x))
    return star_result(e, raised, rest)


def gen_star_handler(fr: Frame, match: BaseException, store: StoreFn | None, unbind: Callable[[Frame], None],
                     hb: GenFn) -> Generator[Any, Any, BaseException | None]:
    """statements.run_star_handler in generator mode."""
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
                yield from hb(fr)
            finally:
                unbind(fr)
    return body.caught


def make_gen_try_finally(attempt: GenFn, final: GenFn) -> GenFn:
    """Run attempt, then final however attempt finishes (including when the
    generator is closed while suspended in attempt).  A signal from final
    wins, even over an exception."""
    def gen_try_finally(fr: Frame) -> Generator[Any, Any, Any]:
        try:
            r: Signal | None = yield from attempt(fr)
        except BaseException:
            f: Signal | None = yield from final(fr)
            if f is not None:
                return f
            raise
        f = yield from final(fr)
        if f is not None:
            return f
        return r
    return gen_try_finally


def gen_with_stmt(comp: Compiler, s: With) -> GenFn:
    """`with` (or `async with`) in generator mode, as nested single-item
    with statements."""
    if s.is_async:
        check_async(comp, "'async with'", s.line)
    inner: GenFn = gen_block(comp, s.body)
    for item in reversed(s.items):
        inner = gen_with_item(comp, item, inner, s.is_async)
    return inner


def gen_with_item(comp: Compiler, item: WithItem, inner: GenFn, is_async: bool) -> GenFn:
    """One context manager around inner, in generator mode."""
    pre, en = hoist(comp, item.expr)
    mc: ExprFn = comp.expr(en)
    store: StoreFn | None = target(comp, item.target) if item.target is not None else None
    if is_async:
        return make_gen_async_with(pre, mc, store, inner)
    return make_gen_with(pre, mc, store, inner)


def make_gen_with(pre: Hoisted, mc: ExprFn, store: StoreFn | None, inner: GenFn) -> GenFn:
    """A with statement in generator mode (see statements.compile_with_item)."""
    def gen_with(fr: Frame) -> Generator[Any, Any, Any]:
        for key, ge in pre:
            fr[key] = yield from ge(fr)
        mgr: Any = mc(fr)
        enter, exit_ = context_methods(mgr)
        v: Any = enter()
        if store is not None:
            store(fr, v)
        try:
            r: Signal | None = yield from inner(fr)
        except BaseException as e:
            ev: Any = exc_value(e)
            if not exit_(exc_type(ev), ev if type(mgr) is Instance else e, e.__traceback__):
                raise
            return None
        exit_(None, None, None)
        return r
    return gen_with


def make_gen_async_with(pre: Hoisted, mc: ExprFn, store: StoreFn | None, inner: GenFn) -> GenFn:
    """`async with`: like with, but the results of __aenter__ and
    __aexit__ are awaited."""
    def gen_async_with(fr: Frame) -> Generator[Any, Any, Any]:
        for key, ge in pre:
            fr[key] = yield from ge(fr)
        mgr: Any = mc(fr)
        enter, exit_ = async_context_methods(mgr)
        v: Any = yield from await_iter(enter())
        if store is not None:
            store(fr, v)
        try:
            r: Signal | None = yield from inner(fr)
        except BaseException as e:
            ev: Any = exc_value(e)
            x: Any = yield from await_iter(exit_(exc_type(ev), ev if type(mgr) is Instance else e, e.__traceback__))
            if not x:
                raise
            return None
        yield from await_iter(exit_(None, None, None))
        return r
    return gen_async_with


def gen_match_stmt(comp: Compiler, s: Match) -> GenFn:
    """`match` in generator mode (see patterns.compile_match)."""
    if any_yield([case.guard for case in s.cases if case.guard is not None]):
        return gen_match_yield_guards(comp, s)
    pre, subject = hoist(comp, s.subject)
    sc: ExprFn = comp.expr(subject)
    cases: list[tuple[PatternFn, ExprFn | None, GenFn]] = []
    for case in s.cases:
        m: PatternFn = pattern(comp, case.pattern)
        guard: ExprFn | None = comp.expr(case.guard) if case.guard is not None else None
        cases.append((m, guard, gen_block(comp, case.body)))

    def gen_match(fr: Frame) -> Generator[Any, Any, Any]:
        for key, ge in pre:
            fr[key] = yield from ge(fr)
        v: Any = sc(fr)
        for m, guard, body in cases:
            if m(fr, v) and (guard is None or guard(fr)):
                r: Signal | None = yield from body(fr)
                return r
        return None
    return gen_match


GEN_STMT_COMPILERS: dict[type, Callable[[Compiler, Any], GenFn]] = {
    If: gen_if_stmt, While: gen_while_stmt, For: gen_for_stmt, Try: gen_try_stmt,
    With: gen_with_stmt, Match: gen_match_stmt,
}


# -- statements whose evaluation order around a yield matters ---------------------------
#
# Hoisting evaluates every yield of a statement before the rest of it.  These
# statements instead evaluate their parts in the order CPython does.


def gen_assign_stmt(comp: Compiler, s: Assign) -> GenFn:
    """`t1 = t2 = value` in generator mode: the value first, then each
    target from left to right, including any yield in a target."""
    if not any_yield(s.targets):
        name: str | None = comp.local_name(s.targets[0]) if len(s.targets) == 1 else None
        if name is not None and type(s.value) is Yield and not contains_yield_value(s.value) \
                and not in_async_function(comp):
            return make_yield_to_local(name, comp.expr(s.value.value or Const(s.line, None)))
        return gen_simple_stmt(comp, s)
    return make_gen_assign(gen_expr(comp, s.value), [gen_target(comp, t) for t in s.targets])


def contains_yield_value(n: Yield) -> bool:
    """Does the value of `yield value` itself contain a yield?"""
    return n.value is not None and contains_yield(n.value)


def make_yield_to_local(name: str, vc: ExprFn) -> GenFn:
    """`name = yield value` for a local variable, the commonest statement
    with a yield, in a single generator (as in the yield points below)."""
    def yield_to_local(fr: Frame) -> Generator[Any, Any, Any]:
        try:
            fr[name] = yield vc(fr)
            return None
        except StopIteration as e:
            raise carry_stop(e) from None
        except GenClose:
            raise GeneratorExit from None
    return yield_to_local


def make_gen_assign(vg: GenFn, stores: list[GenStoreFn]) -> GenFn:
    """Evaluate vg and store its value through each of stores."""
    def gen_assign(fr: Frame) -> Generator[Any, Any, Any]:
        v: Any = yield from vg(fr)
        for st in stores:
            yield from st(fr, v)
        return None
    return gen_assign


def gen_target(comp: Compiler, t: Expression) -> GenStoreFn:
    """An assignment target in generator mode: like targets.target, but a
    yield in the target's sub-expressions may suspend the generator."""
    if not contains_yield(t):
        return make_gstore_plain(target(comp, t))
    if type(t) is Attribute:
        return make_gstore_attr(gen_expr(comp, t.value), t.attr)
    if type(t) is Subscript:
        return make_gstore_item(gen_expr(comp, t.value), gen_expr(comp, t.index))
    if type(t) is Tuple or type(t) is List:
        star: int = -1
        stores: list[GenStoreFn] = []
        for i, e in enumerate(t.elts):
            if type(e) is Starred:
                star = i
                e = e.value
            stores.append(gen_target(comp, e))
        return make_gstore_unpack(stores, star)
    target(comp, t)  # raises the SyntaxError for a target that cannot be assigned
    raise SyntaxError(f'cannot assign to {type(t).__name__}')


def make_gstore_plain(store: StoreFn) -> GenStoreFn:
    """A target without a yield."""
    def gstore_plain(fr: Frame, v: Any) -> Generator[Any, Any, Any]:
        store(fr, v)
        return None
        yield
    return gstore_plain


def make_gstore_attr(og: GenFn, name: str) -> GenStoreFn:
    """`obj.name = value`."""
    def gstore_attr(fr: Frame, v: Any) -> Generator[Any, Any, Any]:
        o: Any = yield from og(fr)
        setattr_any(o, name, v)
    return gstore_attr


def make_gstore_item(og: GenFn, ig: GenFn) -> GenStoreFn:
    """`obj[index] = value`."""
    def gstore_item(fr: Frame, v: Any) -> Generator[Any, Any, Any]:
        o: Any = yield from og(fr)
        i: Any = yield from ig(fr)
        o[i] = v
    return gstore_item


def make_gstore_unpack(stores: list[GenStoreFn], star: int) -> GenStoreFn:
    """`a, *b, c = value`: unpack the value (the element at index star, if
    any, takes a list), then store the items one target at a time."""
    n: int = len(stores)

    def gstore_unpack(fr: Frame, v: Any) -> Generator[Any, Any, Any]:
        items: Any = unpack(v, n) if star < 0 else unpack_starred(v, n, star)
        for i, st in enumerate(stores):
            yield from st(fr, items[i])
    return gstore_unpack


def unpack_starred(v: Any, n: int, star: int) -> list[Any]:
    """The values for n targets of which the one at index star is starred
    (it gets a list of the items between the others)."""
    try:
        items: list[Any] = list(v)
    except TypeError:
        raise TypeError(f'cannot unpack non-iterable {type_name(v)} object') from None
    m: int = len(items)
    if m < n - 1:
        raise ValueError(f'not enough values to unpack (expected at least {n - 1}, got {m})')
    after: int = n - star - 1
    return items[:star] + [items[star:m - after]] + items[m - after:]


def gen_delete_stmt(comp: Compiler, s: Delete) -> GenFn:
    """`del t1, t2, ...` where a target contains a yield."""
    return make_gen_delete([gen_del_target(comp, t) for t in s.targets])


def make_gen_delete(ds: list[GenFn]) -> GenFn:
    """Run the deletions ds in order."""
    def gen_delete(fr: Frame) -> Generator[Any, Any, Any]:
        for d in ds:
            yield from d(fr)
        return None
    return gen_delete


def gen_del_target(comp: Compiler, t: Expression) -> GenFn:
    """A `del` target in generator mode."""
    if not contains_yield(t):
        return make_plain_stmt(del_target(comp, t))
    if type(t) is Attribute:
        return make_gdel_attr(gen_expr(comp, t.value), t.attr)
    if type(t) is Subscript:
        return make_gdel_item(gen_expr(comp, t.value), gen_expr(comp, t.index))
    if type(t) is Tuple or type(t) is List:
        return make_gen_delete([gen_del_target(comp, e) for e in t.elts])
    del_target(comp, t)  # raises the SyntaxError for a target that cannot be deleted
    raise SyntaxError(f'cannot delete {type(t).__name__}')


def make_plain_stmt(c: StmtFn) -> GenFn:
    """A statement without a yield, as a generator that never yields."""
    def plain_stmt(fr: Frame) -> Generator[Any, Any, Any]:
        return c(fr)
        yield
    return plain_stmt


def make_gdel_attr(og: GenFn, name: str) -> GenFn:
    """`del obj.name`."""
    def gdel_attr(fr: Frame) -> Generator[Any, Any, Any]:
        o: Any = yield from og(fr)
        delattr_any(o, name)
    return gdel_attr


def make_gdel_item(og: GenFn, ig: GenFn) -> GenFn:
    """`del obj[index]`."""
    def gdel_item(fr: Frame) -> Generator[Any, Any, Any]:
        o: Any = yield from og(fr)
        i: Any = yield from ig(fr)
        del o[i]
    return gdel_item


def gen_augassign_stmt(comp: Compiler, s: AugAssign) -> GenFn:
    """`target op= value` in generator mode: the target is evaluated and its
    current value loaded before the value, which may suspend the generator
    (as in CPython, an update made meanwhile is lost)."""
    t: Expression = s.target
    iop: Callable[[Any, Any], Any] = INPLACE_OPS[s.op]
    vg: GenFn = gen_expr(comp, s.value)
    if type(t) is Name:
        return make_gen_iop_name(load_name(comp, t.id), store_name(comp, t.id), iop, vg)
    if type(t) is Attribute:
        return make_gen_iop_attr(gen_expr(comp, t.value), t.attr, iop, vg)
    if type(t) is Subscript:
        return make_gen_iop_item(gen_expr(comp, t.value), gen_expr(comp, t.index), iop, vg)
    raise SyntaxError(f"'{type(t).__name__}' is an illegal expression for augmented assignment")


def make_gen_iop_name(load: ExprFn, store: StoreFn, iop: Callable[[Any, Any], Any], vg: GenFn) -> GenFn:
    """`name op= value`."""
    def gen_iop_name(fr: Frame) -> Generator[Any, Any, Any]:
        old: Any = load(fr)
        v: Any = yield from vg(fr)
        store(fr, iop(old, v))
    return gen_iop_name


def make_gen_iop_attr(og: GenFn, name: str, iop: Callable[[Any, Any], Any], vg: GenFn) -> GenFn:
    """`obj.name op= value`."""
    def gen_iop_attr(fr: Frame) -> Generator[Any, Any, Any]:
        o: Any = yield from og(fr)
        old: Any = getattr_any(o, name)
        v: Any = yield from vg(fr)
        setattr_any(o, name, iop(old, v))
    return gen_iop_attr


def make_gen_iop_item(og: GenFn, ig: GenFn, iop: Callable[[Any, Any], Any], vg: GenFn) -> GenFn:
    """`obj[index] op= value`."""
    def gen_iop_item(fr: Frame) -> Generator[Any, Any, Any]:
        o: Any = yield from og(fr)
        i: Any = yield from ig(fr)
        old: Any = o[i]
        v: Any = yield from vg(fr)
        o[i] = iop(old, v)
    return gen_iop_item


def gen_assert_stmt(comp: Compiler, s: Assert) -> GenFn:
    """`assert test, msg` in generator mode: the message is evaluated only
    when the test fails."""
    tg: GenFn = gen_expr(comp, s.test)
    mg: GenFn | None = gen_expr(comp, s.msg) if s.msg is not None else None

    def gen_assert(fr: Frame) -> Generator[Any, Any, Any]:
        t: Any = yield from tg(fr)
        if not t:
            if mg is None:
                raise AssertionError()
            m: Any = yield from mg(fr)
            raise AssertionError(m)
    return gen_assert


def gen_raise_stmt(comp: Compiler, s: Raise) -> GenFn:
    """`raise exc from cause` in generator mode: exc is evaluated before
    cause (an exception class is instantiated after both)."""
    if s.exc is None:
        return gen_simple_stmt(comp, s)
    eg: GenFn = gen_expr(comp, s.exc)
    cg: GenFn | None = gen_expr(comp, s.cause) if s.cause is not None else None

    def gen_raise(fr: Frame) -> Generator[Any, Any, Any]:
        e: Any = yield from eg(fr)
        c: Any = MISSING
        if cg is not None:
            c = yield from cg(fr)
        try:
            raise_exception(e, c)
        except StopIteration as x:
            raise carry_stop(x) from None
    return gen_raise


def raise_exception(e: Any, c: Any) -> None:
    """`raise e from c` (just `raise e` if c is MISSING)."""
    ne: BaseException = to_native_exc(e)
    if c is MISSING:
        raise ne
    if c is None:
        raise ne from None
    raise ne from to_native_exc(c)


def gen_try_yield_types(comp: Compiler, s: Try) -> GenFn:
    """A try statement some of whose except clause types contain a yield:
    the types are evaluated in generator mode while matching an exception."""
    untyped: Try = clone(s)
    untyped.handlers = []
    for h in s.handlers:
        uh: Any = clone(h)
        uh.type = None
        untyped.handlers.append(uh)
    body: GenFn = gen_block(comp, s.body)
    hs: list[Handler] = handlers(comp, untyped, gen_block)
    types: list[GenFn | None] = [gen_expr(comp, h.type) if h.type is not None else None for h in s.handlers]
    orelse: GenFn | None = gen_block(comp, s.orelse) if s.orelse else None
    attempt: GenFn = make_gen_try_yield_types(body, list(zip(types, hs)), orelse)
    if not s.finalbody:
        return attempt
    return make_gen_try_finally(attempt, gen_block(comp, s.finalbody))


def make_gen_try_yield_types(body: GenFn, hs: list[tuple[GenFn | None, Handler]], orelse: GenFn | None) -> GenFn:
    """Like make_gen_try_except, with handler types in generator mode."""
    def gen_try_yield_types(fr: Frame) -> Generator[Any, Any, Any]:
        try:
            r: Signal | None = yield from body(fr)
        except BaseException as e:
            v: Any = exc_value(e)
            h: Handler | None = yield from match_handler(fr, v, hs)
            if h is None:
                raise
            store: StoreFn | None = h[1]
            if store is not None:
                store(fr, v)
            try:
                r = yield from h[3](fr)
            finally:
                if store is not None:
                    h[2](fr)
            return r
        if r is None and orelse is not None:
            r = yield from orelse(fr)
        return r
    return gen_try_yield_types


def match_handler(fr: Frame, v: Any, hs: list[tuple[GenFn | None, Handler]]) -> Generator[Any, Any, Any]:
    """The first handler of hs whose type (evaluated in generator mode)
    matches exception value v, or None."""
    for tg, h in hs:
        if tg is None:
            return h
        typ: Any = yield from tg(fr)
        if exc_matches(v, typ):
            return h
    return None


def gen_match_yield_guards(comp: Compiler, s: Match) -> GenFn:
    """A match statement some of whose guards contain a yield: the guards
    are evaluated in generator mode."""
    pre, subject = hoist(comp, s.subject)
    sc: ExprFn = comp.expr(subject)
    cases: list[tuple[PatternFn, GenFn | None, GenFn]] = []
    for case in s.cases:
        m: PatternFn = pattern(comp, case.pattern)
        guard: GenFn | None = gen_expr(comp, case.guard) if case.guard is not None else None
        cases.append((m, guard, gen_block(comp, case.body)))

    def gen_match_yield_guards(fr: Frame) -> Generator[Any, Any, Any]:
        for key, ge in pre:
            fr[key] = yield from ge(fr)
        v: Any = sc(fr)
        for m, guard, body in cases:
            if m(fr, v):
                ok: Any = True
                if guard is not None:
                    ok = yield from guard(fr)
                if ok:
                    r: Signal | None = yield from body(fr)
                    return r
        return None
    return gen_match_yield_guards


GEN_STMT_COMPILERS.update({
    Assign: gen_assign_stmt, AugAssign: gen_augassign_stmt, Delete: gen_delete_stmt, Assert: gen_assert_stmt,
    Raise: gen_raise_stmt,
})


# -- expressions ------------------------------------------------------------------------


def gen_expr(comp: Compiler, n: Expression) -> GenFn:
    """Compile an expression that may contain a yield into a function
    returning a host generator whose return value is the expression's value.

    Expressions whose evaluation order matters around a yield (and/or,
    conditional expressions, comparisons, :=, yield itself) have their own
    compilers; any other expression evaluates all its children into
    temporaries first (see gen_generic)."""
    if not contains_yield(n):
        return make_plain(comp.expr(n))
    compile_expr: Callable[[Compiler, Any], GenFn] = GEN_EXPR_COMPILERS.get(type(n), gen_generic)
    return compile_expr(comp, n)


def make_plain(c: ExprFn) -> GenFn:
    """An expression without a yield, as a generator that never yields."""
    def plain(fr: Frame) -> Generator[Any, Any, Any]:
        try:
            return c(fr)
        except StopIteration as e:
            raise carry_stop(e) from None
        yield
    return plain


def make_hoisted(pre: Hoisted, c: ExprFn) -> GenFn:
    """Evaluate the hoisted sub-expressions pre, then the normally compiled
    expression c that reads their temporaries."""
    def run_hoisted(fr: Frame) -> Generator[Any, Any, Any]:
        for key, ge in pre:
            fr[key] = yield from ge(fr)
        try:
            return c(fr)
        except StopIteration as e:
            raise carry_stop(e) from None
    return run_hoisted


# The yield points below carry a StopIteration thrown in (or raised by the
# value) and turn the GenClose with which drive() delivers close() into
# GeneratorExit (see the module docstring).

def gen_yield(comp: Compiler, n: Yield) -> GenFn:
    """`yield value`: its value is whatever is sent into the generator."""
    if in_async_function(comp):
        return make_async_gen_yield(gen_expr(comp, n.value) if n.value is not None else None)
    if n.value is None:
        return yield_none
    if not contains_yield(n.value):
        return make_yield_value(comp.expr(n.value))
    return make_yield_nested(gen_expr(comp, n.value))


def yield_none(fr: Frame) -> Generator[Any, Any, Any]:
    """`yield` without a value."""
    try:
        v: Any = yield None
        return v
    except StopIteration as e:
        raise carry_stop(e) from None
    except GenClose:
        raise GeneratorExit from None


def make_yield_value(vc: ExprFn) -> GenFn:
    """`yield value` where value contains no yield."""
    def yield_(fr: Frame) -> Generator[Any, Any, Any]:
        try:
            v: Any = yield vc(fr)
            return v
        except StopIteration as e:
            raise carry_stop(e) from None
        except GenClose:
            raise GeneratorExit from None
    return yield_


def make_yield_nested(vg: GenFn) -> GenFn:
    """`yield value` where value itself contains a yield."""
    def yield_nested(fr: Frame) -> Generator[Any, Any, Any]:
        x: Any = yield from vg(fr)
        try:
            v: Any = yield x
            return v
        except StopIteration as e:
            raise carry_stop(e) from None
        except GenClose:
            raise GeneratorExit from None
    return yield_nested


def make_async_gen_yield(vg: GenFn | None) -> GenFn:
    """`yield value` in an async generator."""
    def async_gen_yield(fr: Frame) -> Generator[Any, Any, Any]:
        x: Any = None
        if vg is not None:
            x = yield from vg(fr)
        v: Any = yield from agen_yield(x)
        return v
    return async_gen_yield


def gen_yield_from(comp: Compiler, n: YieldFrom) -> GenFn:
    """`yield from iterable` delegates to the host's `yield from`."""
    if in_async_function(comp):
        raise SyntaxError(f"'yield from' inside async function ({comp.filename}, line {n.line})")
    vg: GenFn = gen_expr(comp, n.value)

    def yield_from(fr: Frame) -> Generator[Any, Any, Any]:
        it: Any = yield from vg(fr)
        try:
            v: Any = yield from it
            return v
        except StopIteration as e:
            raise carry_stop(e) from None
        except GenClose:
            raise GeneratorExit from None
    return yield_from


def gen_await(comp: Compiler, n: Await) -> GenFn:
    """`await x` yields from the iterator that x's __await__ returns."""
    vg: GenFn = gen_expr(comp, n.value)

    def await_(fr: Frame) -> Generator[Any, Any, Any]:
        x: Any = yield from vg(fr)
        try:
            v: Any = yield from await_iter(x)
            return v
        except StopIteration as e:
            raise carry_stop(e) from None
        except GenClose:
            raise GeneratorExit from None
    return await_


def gen_boolop(comp: Compiler, n: BoolOp) -> GenFn:
    """`a and b ...` / `a or b ...`: operands after the deciding one are
    not evaluated."""
    gs: list[GenFn] = [gen_expr(comp, v) for v in n.values]
    if n.op == 'and':
        return make_gen_and(gs)
    return make_gen_or(gs)


def make_gen_and(gs: list[GenFn]) -> GenFn:
    """`a and b and ...`: the first false operand, or else the last one."""
    def gen_and(fr: Frame) -> Generator[Any, Any, Any]:
        v: Any = None
        for ge in gs:
            v = yield from ge(fr)
            if not v:
                return v
        return v
    return gen_and


def make_gen_or(gs: list[GenFn]) -> GenFn:
    """`a or b or ...`: the first true operand, or else the last one."""
    def gen_or(fr: Frame) -> Generator[Any, Any, Any]:
        v: Any = None
        for ge in gs:
            v = yield from ge(fr)
            if v:
                return v
        return v
    return gen_or


def gen_ifexp(comp: Compiler, n: IfExp) -> GenFn:
    """`body if test else orelse`: only the chosen branch is evaluated."""
    tg: GenFn = gen_expr(comp, n.test)
    bg: GenFn = gen_expr(comp, n.body)
    og: GenFn = gen_expr(comp, n.orelse)

    def gen_ifexp(fr: Frame) -> Generator[Any, Any, Any]:
        c: Any = yield from tg(fr)
        if c:
            v: Any = yield from bg(fr)
        else:
            v = yield from og(fr)
        return v
    return gen_ifexp


def gen_compare(comp: Compiler, n: Compare) -> GenFn:
    """`a < b < c ...`: stops at the first false comparison, without
    evaluating the remaining operands."""
    lg: GenFn = gen_expr(comp, n.left)
    gs: list[GenFn] = [gen_expr(comp, c) for c in n.comparators]
    fns: list[Callable[[Any, Any], Any]] = [COMPARE_FUNCS[o] for o in n.ops]
    pairs: list[tuple[Callable[[Any, Any], Any], GenFn]] = list(zip(fns, gs))

    def gen_compare(fr: Frame) -> Generator[Any, Any, Any]:
        a: Any = yield from lg(fr)
        r: Any = True
        for fn, ge in pairs:
            b: Any = yield from ge(fr)
            try:
                r = fn(a, b)
            except StopIteration as e:
                raise carry_stop(e) from None
            if not r:
                return r
            a = b
        return r
    return gen_compare


def gen_namedexpr(comp: Compiler, n: NamedExpr) -> GenFn:
    """`name := value`."""
    vg: GenFn = gen_expr(comp, n.value)
    store: StoreFn = store_name(comp, n.target.id)

    def gen_named(fr: Frame) -> Generator[Any, Any, Any]:
        v: Any = yield from vg(fr)
        store(fr, v)
        return v
    return gen_named


def gen_comprehension(comp: Compiler, n: ListComp | SetComp | DictComp | GeneratorExp) -> GenFn:
    """A comprehension: only its first iterable is evaluated in this scope,
    so only that can be hoisted.  An asynchronous list, set or dict
    comprehension runs in generator mode as a whole."""
    if not isinstance(n, GeneratorExp) and is_async_comp(n):
        from .comprehensions import compile_async_comprehension
        return compile_async_comprehension(comp, n, COMP_KINDS[type(n)])
    new: ListComp | SetComp | DictComp | GeneratorExp = clone(n)
    first: Comprehension = clone(n.gens[0])
    pre: Hoisted = []
    first.iter = hoist_expr(comp, n.gens[0].iter, pre)
    new.gens = [first] + n.gens[1:]
    return make_hoisted(pre, comp.expr(new))


def gen_generic(comp: Compiler, n: Expression) -> GenFn:
    """Any other expression: evaluate every child expression into a
    temporary (in order), then evaluate the node itself on the temporaries."""
    new: Expression = clone(n)
    pre: Hoisted = []
    for f in n._fields:
        v: Any = getattr(n, f)
        if isinstance(v, Node):
            setattr(new, f, hoist_child(comp, v, pre))
        elif type(v) is list:
            setattr(new, f, [hoist_child(comp, x, pre) if isinstance(x, Node) else x for x in v])
    return make_hoisted(pre, comp.expr(new))


GEN_EXPR_COMPILERS: dict[type, Callable[[Compiler, Any], GenFn]] = {
    Yield: gen_yield, YieldFrom: gen_yield_from, Await: gen_await, BoolOp: gen_boolop, IfExp: gen_ifexp,
    Compare: gen_compare, NamedExpr: gen_namedexpr, ListComp: gen_comprehension, SetComp: gen_comprehension,
    DictComp: gen_comprehension, GeneratorExp: gen_comprehension,
}


COMP_KINDS: dict[type, str] = {ListComp: 'list', SetComp: 'set', DictComp: 'dict', GeneratorExp: 'gen'}
"""The kind of each comprehension node, as comprehensions.comprehension names it."""


def gen_dict_display(comp: Compiler, n: DictDisplay) -> GenFn:
    """`{k1: v1, **m, k2: v2}`: keys and values are evaluated in order,
    each key before its value."""
    new: DictDisplay = clone(n)
    pre: Hoisted = []
    keys: list[Expression | None] = []
    values: list[Expression] = []
    for k, v in zip(n.keys, n.values):
        keys.append(hoist_expr(comp, k, pre) if k is not None else None)
        values.append(hoist_expr(comp, v, pre))
    new.keys = keys
    new.values = values
    return make_hoisted(pre, comp.expr(new))


def gen_lambda(comp: Compiler, n: Lambda) -> GenFn:
    """A lambda whose default values contain a yield: only the defaults are
    evaluated here (the body belongs to the lambda)."""
    new: Lambda = clone(n)
    pre: Hoisted = []
    new.args = hoist_arguments(comp, n.args, pre)
    return make_hoisted(pre, comp.expr(new))


GEN_EXPR_COMPILERS.update({DictDisplay: gen_dict_display, Lambda: gen_lambda})
