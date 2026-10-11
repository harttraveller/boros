"""Compilation of function and class definitions.

A `def` (or `lambda`) is compiled once into a Code object holding the body
closure and the parameter list.  Each time the `def` statement runs, it
evaluates the decorators and default values and wraps the Code in a new
Function together with the current globals and the enclosing frame (the
closure through which the body reaches its free variables).

A `class` statement runs its body closure in a fresh namespace dict, builds
the class from it with runtime.classes.build_class, and fills the class's
`__class__` cell, which zero-argument `super()` in its methods reads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..lexer import syntax_error
from ..runtime.calls import call
from ..runtime.classes import ClassNamespace, build_class, class_namespace
from ..runtime.coroutines import drive
from ..runtime.objects import Code, Function
from ..runtime.type_alias import make_type_alias
from ..syntax import Const, ExprStmt, Return
from .expressions import build_list, sequence_items
from .generators import gen_body, gen_expr
from .names import store_name
from .scopes import FREE
from .statements import (
    block,
    clean_doc,
    function_body,
    has_annotations,
    make_run_block,
    real_statements,
    setup_annotations,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from ..core_types import ExprFn, Frame, GenFn, StmtFn, StoreFn
    from ..runtime.objects import Class
    from ..syntax import Arguments, ClassDef, Expression, FunctionDef, Lambda, Scope, Statement, TypeAlias
    from .compiler import Compiler


def compile_lambda(comp: Compiler, n: Lambda) -> ExprFn:
    """Compile a lambda expression: it evaluates to a new Function."""
    code: Code = compile_code(comp, '<lambda>', comp.qualname('<lambda>'), n.args, n.body, n.scope, n.line, True)
    return make_function(comp, code, n.args, [])


def compile_type_alias(comp: Compiler, n: TypeAlias) -> ExprFn:
    """The value of `type X[params] = value`: a new type alias, whose value
    the lambda n.compute evaluates when it is first needed."""
    compute: ExprFn = compile_lambda(comp, n.compute)
    name: str = n.name
    params: list[tuple[str, str]] = n.params

    def type_alias(fr: Frame) -> Any:
        return make_type_alias(name, params, compute(fr))
    return type_alias


def compile_funcdef(comp: Compiler, s: FunctionDef) -> StmtFn:
    """Compile a `def` statement: create the Function and bind its name."""
    code: Code = compile_code(comp, s.name, comp.qualname(s.name), s.args, s.body, s.scope, s.line, False)
    make: ExprFn = make_function(comp, code, s.args, s.decorators)
    store: StoreFn = store_name(comp, s.name)

    def funcdef(fr: Frame) -> None:
        store(fr, make(fr))
    return funcdef


def make_function(comp: Compiler, code: Code, args: Arguments, decorators: list[Expression]) -> ExprFn:
    """A closure creating a Function for `code` each time the definition
    runs: it evaluates the decorators (first) and the default values, links
    the function to the current frame (its closure), and applies the
    decorators innermost first."""
    decos: list[ExprFn] = [comp.expr(d) for d in decorators]
    defaults: list[ExprFn] = [comp.expr(d) for d in args.defaults]
    kwdefaults: list[tuple[str, ExprFn]] = []
    for name, d in zip(args.kwonly, args.kw_defaults):
        if d is not None:
            kwdefaults.append((name, comp.expr(d)))
    anns: list[tuple[str, ExprFn]] | None = annotation_closures(comp, code, args)
    mode: int = comp.closure_mode()
    g: Frame = comp.g
    uses_class: bool = code.uses_class

    def make(fr: Frame) -> Any:
        dv: list[Any] = [d(fr) for d in decos]
        defs: tuple[Any, ...] | None = tuple([d(fr) for d in defaults]) if defaults else None
        kwd: dict[str, Any] | None = None
        if kwdefaults:
            kwd = {}
            for name, c in kwdefaults:
                kwd[name] = c(fr)
        if mode == 0:
            clo: Frame | None = fr
        elif mode == 1:
            clo = fr.get('.up')
        else:
            clo = None
        cell: Any = fr.get('.cls') if uses_class else None
        f: Any = Function(code, g, defs, kwd, clo, cell)
        if anns is not None:
            f.annotations = evaluate_annotations(anns, fr)
        i: int = len(dv) - 1
        while i >= 0:
            f = call(dv[i], (f,), None)
            i -= 1
        return f
    return make


def annotation_closures(comp: Compiler, code: Code, args: Arguments) -> list[tuple[str, ExprFn]] | None:
    """The annotations of a function that must be evaluated each time its
    `def` runs, compiled, or None if there are none.  Constant annotations
    (strings, and all of them under `from __future__ import annotations`)
    are stored in the Code instead, and __annotations__ is made from them
    the first time it is read, so that most definitions pay nothing for
    their annotations."""
    anns: list[tuple[str, Expression]] = args.annotations
    if not anns:
        return None
    consts: list[tuple[str, Any]] = [(name, a.value) for name, a in anns if type(a) is Const]
    if len(consts) == len(anns):
        code.annotations = tuple(consts)
        return None
    return [(name, comp.expr(a)) for name, a in anns]


def evaluate_annotations(anns: list[tuple[str, ExprFn]], fr: Frame) -> dict[str, Any]:
    """The __annotations__ dict of a new function: its compiled annotations
    evaluated in the defining frame, in order."""
    d: dict[str, Any] = {}
    for name, c in anns:
        d[name] = c(fr)
    return d


def compile_code(comp: Compiler, name: str, qualname: str, args: Arguments, body: list[Statement] | Expression,
                 scope: Scope, line: int, is_lambda: bool) -> Code:
    """Compile the body of a function or lambda into a Code object.

    body is the list of statements of a `def`, or the single expression of
    a lambda (is_lambda).  Generator functions (and async functions, which
    run as generators) get a generator-mode body.  The compiler's current
    code name and temporary counter are saved and restored around the body.
    """
    declare_parameters(scope, args)
    is_async: bool = scope.is_async
    is_gen: bool = scope.is_gen or is_async
    comp.stack.append(scope)
    check_nonlocals(comp, scope)
    saved: str = comp.code_name
    saved_temps: int = comp.ntemps
    comp.code_name = name
    if isinstance(body, list):
        fbody, doc, code_line = compile_def_body(comp, body, is_gen, line)
    else:
        fbody, doc, code_line = compile_lambda_body(comp, body, is_gen), None, line
    comp.code_name = saved
    comp.ntemps = saved_temps
    comp.stack.pop()
    if scope.uses_class:
        propagate_class_cell(comp)
    code: Code = Code(name, qualname, comp.filename, code_line, args, fbody, scope, doc)
    code.co_firstlineno = line
    code.is_gen = is_gen
    code.is_async = is_async
    if is_gen or code.uses_class:
        code.fastn = -1
    return code


def check_nonlocals(comp: Compiler, scope: Scope) -> None:
    """Check that every name declared nonlocal in `scope` (the innermost
    scope being compiled) is bound in an enclosing function."""
    for x in scope.decl_lines:
        if x in scope.nonlocals and comp.resolve_outer(x, len(comp.stack) - 1)[0] is not FREE:
            raise syntax_error(f"no binding for nonlocal '{x}' found", comp.filename, scope.decl_lines[x])


def declare_parameters(scope: Scope, args: Arguments) -> None:
    """Record the parameter names in the function's scope."""
    scope.argnames = args.posonly + args.args
    scope.vararg = args.vararg
    params: set[str] = set(args.posonly + args.args + args.kwonly)
    if args.vararg is not None:
        params.add(args.vararg)
    if args.kwarg is not None:
        params.add(args.kwarg)
    scope.params = params


def compile_def_body(comp: Compiler, body: list[Statement], is_gen: bool,
                     line: int) -> tuple[ExprFn, str | None, int]:
    """Compile the statements of a `def`.  Returns (body closure, docstring,
    line), where line is the source line reported for the function in
    tracebacks (that of its last statement if it ends with `return` or has
    a single statement, else that of its first)."""
    doc: str | None = docstring(body)
    real: list[Statement] = real_statements(body)
    code_line: int = line
    if real:
        code_line = real[-1].line if (type(real[-1]) is Return or len(real) == 1) else real[0].line
    fbody: ExprFn = gen_body(comp, body) if is_gen else function_body(comp, body)
    return fbody, doc, code_line


def compile_lambda_body(comp: Compiler, body: Expression, is_gen: bool) -> ExprFn:
    """Compile the expression of a lambda.  A lambda containing `yield` is a
    generator function whose return value is the expression's value."""
    if not is_gen:
        return comp.expr(body)
    return make_genlambda(gen_expr(comp, body))


def make_genlambda(ge: GenFn) -> ExprFn:
    """The body of a generator lambda: run the generator-mode expression."""

    def run_genlambda(fr: Frame) -> Generator[Any, Any, Any]:
        return drive(ge(fr), fr, 1)
    return run_genlambda


def docstring(body: list[Statement]) -> str | None:
    """The docstring of a def or class body: its first statement, if that is
    a string literal."""
    if body:
        first: Statement = body[0]
        if type(first) is ExprStmt and type(first.value) is Const and type(first.value.value) is str:
            return clean_doc(first.value.value)
    return None


def propagate_class_cell(comp: Compiler) -> None:
    """A function that uses `__class__` (or zero-argument super()) needs the
    class cell of the class it is defined in; mark every function scope
    between it and that class as using it too, so the cell is passed down."""
    for s in reversed(comp.stack):
        if s.kind == 'class' or s.kind == 'module':
            break
        s.uses_class = True


def class_keyword_values(kws: list[tuple[str | None, ExprFn]], fr: Frame) -> dict[str, Any]:
    """Evaluate the keyword arguments of a class statement (`metaclass=M`,
    `**options`, ...)."""
    kw: dict[str, Any] = {}
    for k, c in kws:
        if k is None:
            kw.update(c(fr))
        else:
            kw[k] = c(fr)
    return kw


def new_class_namespace(fr: Frame, g: Frame, qualname: str, doc: str | None, mode: int,
                        uses_locals: bool) -> dict[str, Any]:
    """The fresh namespace a class body runs in: __module__, __qualname__
    and __doc__, plus the '.up' link to the enclosing function's frame (mode
    is the Compiler.closure_mode where the class statement is).  A body
    that calls locals() gets a ClassNamespace, which locals() can return."""
    ns: dict[str, Any] = {'__module__': g.get('__name__'), '__qualname__': qualname}
    if uses_locals:
        ns = ClassNamespace(ns)
    if doc is not None:
        ns['__doc__'] = doc
    if mode == 0:
        ns['.up'] = fr
    elif mode == 1:
        ns['.up'] = fr.get('.up')
    return ns


def compile_classdef(comp: Compiler, s: ClassDef) -> StmtFn:
    """Compile a `class` statement."""
    decos: list[ExprFn] = [comp.expr(d) for d in s.decorators]
    _, bitems = sequence_items(comp, s.bases)
    build_bases: ExprFn = build_list(comp, bitems)
    kws: list[tuple[str | None, ExprFn]] = [(k.arg, comp.expr(k.value)) for k in s.keywords]
    store: StoreFn = store_name(comp, s.name)
    mode: int = comp.closure_mode()
    g: Frame = comp.g
    qualname: str = comp.qualname(s.name)
    name: str = s.name
    doc: str | None = docstring(s.body)
    comp.stack.append(s.scope)
    check_nonlocals(comp, s.scope)
    saved: str = comp.code_name
    comp.code_name = name
    body: StmtFn = block(comp, s.body)
    if has_annotations(s.body):
        body = make_run_block(comp, [setup_annotations, body], [s.line, s.line])
    comp.code_name = saved
    comp.stack.pop()
    uses_locals: bool = s.scope.uses_locals

    def classdef(fr: Frame) -> None:
        """Run the class statement: evaluate decorators, bases and keywords,
        run the body in a fresh namespace, build the class and bind it."""
        dv: list[Any] = [d(fr) for d in decos]
        bases: list[Any] = build_bases(fr)
        kw: dict[str, Any] = class_keyword_values(kws, fr)
        ns: dict[str, Any] = new_class_namespace(fr, g, qualname, doc, mode, uses_locals)
        cell: list[Class | None] = [None]
        ns['.cls'] = cell
        ns = class_namespace(name, bases, kw, ns)
        body(ns)
        ns.pop('.up', None)
        del ns['.cls']
        if uses_locals:
            ns = dict(ns.items())
        cls: Any = build_class(name, bases, ns, kw)
        cell[0] = cls
        i: int = len(dv) - 1
        while i >= 0:
            cls = call(dv[i], (cls,), None)
            i -= 1
        store(fr, cls)
    return classdef
