"""Compilation of list/set/dict comprehensions and generator expressions.

A comprehension such as `[f(x) for x in xs if x]` runs in its own scope, so
its loop variables do not leak.  At run time each evaluation creates a small
frame for that scope (linked to the enclosing function's frame through
'.up', so free variables resolve as in a nested function), evaluates the
first iterable in the *enclosing* frame (as Python does), and then runs the
`for`/`if` clauses as nested loops in the comprehension frame.

Each clause is compiled to a tuple (name, store, iterable, conditions):

* name: the loop target if it is a plain name, so the loops can assign it
  with a direct frame write; otherwise None and `store` is used;
* store: the compiled assignment target (used when name is None);
* iterable: the clause's iterable (for the first clause, the closure that
  is evaluated in the enclosing frame);
* conditions: the compiled `if` filters.

The kinds of comprehension differ only in what they do with each element,
so each has its own small closure; one-clause list comprehensions over a
plain name, the most common kind, get dedicated fast closures.

Asynchronous comprehensions (with `async for` clauses, or an await outside
the first iterable) are compiled in generator mode; see the last section.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..runtime.coroutines import agen_yield, async_generator, await_value, drive
from ..runtime.protocols import aiter_of, anext_awaitable
from ..syntax import Comprehension, DictComp, Name, collect_target_names
from .generators import check_comp_yield, gen_expr, in_async_function, is_async_comp, make_plain
from .scopes import comprehension_scope
from .targets import target

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable

    from ..core_types import ExprFn, Frame, GenFn, StoreFn
    from ..syntax import GeneratorExp, ListComp, Scope, SetComp
    from .compiler import Compiler

    # One compiled `for ... in ... if ...` clause; see the module docstring.
    Clause = tuple[str | None, StoreFn, ExprFn, list[ExprFn]]

    # Any comprehension node.
    AnyComp = ListComp | SetComp | DictComp | GeneratorExp

    # A clause of an asynchronous comprehension: (store, iterable, conditions,
    # is `async for`), with the iterable and conditions in generator mode.
    AsyncClause = tuple[StoreFn, GenFn, list[GenFn], bool]

    # Runs clause i of an asynchronous comprehension over iterable `it` in
    # the comprehension frame: run(cfr, it, i, out).
    AsyncLoopFn = Callable[[Frame, Any, int, Any], Generator[Any, Any, Any]]

    # What an asynchronous comprehension does with each element: emit(cfr, out).
    EmitFn = Callable[[Frame, Any], Generator[Any, Any, Any]]

# The scope name of each kind of comprehension, as shown in tracebacks.
COMP_NAMES: dict[str, str] = {'list': '<listcomp>', 'set': '<setcomp>', 'dict': '<dictcomp>', 'gen': '<genexpr>'}


def nested_frame(fr: Frame) -> Frame:
    """The frame of a comprehension inside a function or comprehension."""
    return {'.up': fr}


def class_frame(fr: Frame) -> Frame:
    """The frame of a comprehension in a class body: class-level names are
    not visible inside, so it links to the class body's own outer frame."""
    return {'.up': fr.get('.up')}


def module_frame(fr: Frame) -> Frame:
    """The frame of a comprehension at module level: names not bound in the
    comprehension are globals."""
    return {}


# Comprehension frame makers, indexed by Compiler.closure_mode().
NEW_FRAME: tuple[Callable[[Frame], Frame], ...] = (nested_frame, class_frame, module_frame)


def frame_maker(comp: Compiler, kind: str) -> Callable[[Frame], Frame]:
    """How a comprehension of this kind, compiled in the current scope,
    makes its frame.  At the top level of exec()/eval() code with a
    separate locals mapping, an inlined (list, set or dict) comprehension
    links to the mapping, which it reads (PEP 709); a generator expression
    sees only the globals."""
    if comp.stack[-1].exec_locals and kind != 'gen':
        return nested_frame
    return NEW_FRAME[comp.closure_mode()]


def comprehension(comp: Compiler, n: AnyComp, kind: str) -> ExprFn:
    """Compile a comprehension of the given kind ('list', 'set', 'dict' or 'gen')."""
    check_not_async(comp, n)
    gens: list[Comprehension] = n.gens
    for gen in gens:
        if type(gen) is not Comprehension:
            raise SyntaxError('bad comprehension')
    first_iter: ExprFn = comp.expr(gens[0].iter)
    new_frame: Callable[[Frame], Frame] = frame_maker(comp, kind)
    assigned: set[str] = set()
    for gen in gens:
        collect_target_names(gen.target, assigned)
    qualname: str = comp.qualname('<genexpr>')
    scope: Scope = comprehension_scope(assigned, COMP_NAMES[kind])
    # since Python 3.12, all but generator expressions are inlined (PEP 709)
    scope.inlined = kind != 'gen'
    comp.stack.append(scope)
    loops: list[Clause] = compile_clauses(comp, gens, first_iter)
    kc, ec = compile_element(comp, n)
    comp.stack.pop()
    if kind == 'gen':
        return make_genexp(first_iter, new_frame, loops, ec, qualname)
    if kc is not None:
        return make_dictcomp(first_iter, new_frame, loops, kc, ec)
    if kind == 'set':
        return make_setcomp(first_iter, new_frame, loops, ec)
    return list_comprehension(first_iter, new_frame, loops, ec)


def compile_clauses(comp: Compiler, gens: list[Comprehension], first_iter: ExprFn) -> list[Clause]:
    """Compile the `for` clauses (inside the comprehension's scope)."""
    loops: list[Clause] = []
    for i, gen in enumerate(gens):
        tname: str | None = gen.target.id if type(gen.target) is Name else None
        store: StoreFn = target(comp, gen.target)
        itc: ExprFn = comp.expr(gen.iter) if i > 0 else first_iter
        conds: list[ExprFn] = [comp.expr(c) for c in gen.ifs]
        loops.append((tname, store, itc, conds))
    return loops


def compile_element(comp: Compiler, n: AnyComp) -> tuple[ExprFn | None, ExprFn]:
    """Compile what the comprehension produces: (key, value) closures for a
    dict comprehension, (None, element) otherwise."""
    if isinstance(n, DictComp):
        return comp.expr(n.key), comp.expr(n.value)
    return None, comp.expr(n.elt)


def list_comprehension(first_iter: ExprFn, new_frame: Callable[[Frame], Frame], loops: list[Clause],
                       ec: ExprFn) -> ExprFn:
    """Choose the closure for a list comprehension."""
    tname, _store, _iter, conds = loops[0]
    if len(loops) == 1 and tname is not None:
        if not conds:
            return make_listcomp1(first_iter, new_frame, tname, ec)
        if len(conds) == 1:
            return make_listcomp1if(first_iter, new_frame, tname, conds[0], ec)
    return make_listcomp(first_iter, new_frame, loops, ec)


def make_listcomp1(first_iter: ExprFn, new_frame: Callable[[Frame], Frame], tname: str, ec: ExprFn) -> ExprFn:
    """`[elt for name in it]`."""

    def listcomp1(fr: Frame) -> list[Any]:
        cfr: Frame = new_frame(fr)
        out: list[Any] = []
        for x in first_iter(fr):
            cfr[tname] = x
            out.append(ec(cfr))
        return out
    return listcomp1


def make_listcomp1if(first_iter: ExprFn, new_frame: Callable[[Frame], Frame], tname: str, cond: ExprFn,
                     ec: ExprFn) -> ExprFn:
    """`[elt for name in it if cond]`."""

    def listcomp1if(fr: Frame) -> list[Any]:
        cfr: Frame = new_frame(fr)
        out: list[Any] = []
        for x in first_iter(fr):
            cfr[tname] = x
            if cond(cfr):
                out.append(ec(cfr))
        return out
    return listcomp1if


# The general closures below run clause i over iterator `it` and recurse for
# clause i + 1, whose iterable is evaluated afresh for each element of
# clause i (so it can depend on the outer loop variables); the innermost
# clause produces the elements.

def make_listcomp(first_iter: ExprFn, new_frame: Callable[[Frame], Frame], loops: list[Clause],
                  ec: ExprFn) -> ExprFn:
    """A list comprehension with any number of clauses and any targets."""
    nloops: int = len(loops)

    def run_loops(cfr: Frame, it: Iterable[Any], i: int, out: list[Any]) -> None:
        tname, store, _itc, conds = loops[i]
        last: bool = i == nloops - 1
        for x in it:
            if tname is not None:
                cfr[tname] = x
            else:
                store(cfr, x)
            ok: bool = True
            for c in conds:
                if not c(cfr):
                    ok = False
                    break
            if ok:
                if not last:
                    run_loops(cfr, loops[i + 1][2](cfr), i + 1, out)
                else:
                    out.append(ec(cfr))

    def run_listcomp(fr: Frame) -> list[Any]:
        out: list[Any] = []
        run_loops(new_frame(fr), first_iter(fr), 0, out)
        return out
    return run_listcomp


def make_setcomp(first_iter: ExprFn, new_frame: Callable[[Frame], Frame], loops: list[Clause],
                 ec: ExprFn) -> ExprFn:
    """A set comprehension `{elt for ...}`."""
    nloops: int = len(loops)

    def run_loops(cfr: Frame, it: Iterable[Any], i: int, out: set[Any]) -> None:
        tname, store, _itc, conds = loops[i]
        last: bool = i == nloops - 1
        for x in it:
            if tname is not None:
                cfr[tname] = x
            else:
                store(cfr, x)
            ok: bool = True
            for c in conds:
                if not c(cfr):
                    ok = False
                    break
            if ok:
                if not last:
                    run_loops(cfr, loops[i + 1][2](cfr), i + 1, out)
                else:
                    out.add(ec(cfr))

    def run_setcomp(fr: Frame) -> set[Any]:
        out: set[Any] = set()
        run_loops(new_frame(fr), first_iter(fr), 0, out)
        return out
    return run_setcomp


def make_dictcomp(first_iter: ExprFn, new_frame: Callable[[Frame], Frame], loops: list[Clause],
                  kc: ExprFn, ec: ExprFn) -> ExprFn:
    """A dict comprehension `{key: value for ...}`; the key is evaluated
    before the value."""
    nloops: int = len(loops)

    def run_loops(cfr: Frame, it: Iterable[Any], i: int, out: dict[Any, Any]) -> None:
        tname, store, _itc, conds = loops[i]
        last: bool = i == nloops - 1
        for x in it:
            if tname is not None:
                cfr[tname] = x
            else:
                store(cfr, x)
            ok: bool = True
            for c in conds:
                if not c(cfr):
                    ok = False
                    break
            if ok:
                if not last:
                    run_loops(cfr, loops[i + 1][2](cfr), i + 1, out)
                else:
                    k: Any = kc(cfr)
                    out[k] = ec(cfr)

    def run_dictcomp(fr: Frame) -> dict[Any, Any]:
        out: dict[Any, Any] = {}
        run_loops(new_frame(fr), first_iter(fr), 0, out)
        return out
    return run_dictcomp


def make_genexp(first_iter: ExprFn, new_frame: Callable[[Frame], Frame], loops: list[Clause],
                ec: ExprFn, qualname: str) -> ExprFn:
    """A generator expression `(elt for ...)`.  The first iterable is
    evaluated (and iter() called on it) immediately; everything else runs
    lazily inside the host generator returned, named `qualname`."""
    nloops: int = len(loops)

    def genexp(fr: Frame) -> Any:
        it: Iterable[Any] = iter(first_iter(fr))
        # A host generator object; its __name__ and __qualname__ are writable.
        g: Any = gen_loop(new_frame(fr), it, 0)
        g.__name__ = '<genexpr>'
        g.__qualname__ = qualname
        return g

    def gen_loop(cfr: Frame, it: Iterable[Any], i: int) -> Generator[Any]:
        tname, store, _itc, conds = loops[i]
        last: bool = i == nloops - 1
        for x in it:
            if tname is not None:
                cfr[tname] = x
            else:
                store(cfr, x)
            ok: bool = True
            for c in conds:
                if not c(cfr):
                    ok = False
                    break
            if ok:
                if last:
                    yield ec(cfr)
                else:
                    yield from gen_loop(cfr, loops[i + 1][2](cfr), i + 1)
    return genexp


def compile_listcomp(comp: Compiler, n: ListComp) -> ExprFn:
    """Compile `[elt for ...]`."""
    return comprehension(comp, n, 'list')


def compile_setcomp(comp: Compiler, n: SetComp) -> ExprFn:
    """Compile `{elt for ...}`."""
    return comprehension(comp, n, 'set')


def compile_dictcomp(comp: Compiler, n: DictComp) -> ExprFn:
    """Compile `{key: value for ...}`."""
    return comprehension(comp, n, 'dict')


def compile_genexp(comp: Compiler, n: GeneratorExp) -> ExprFn:
    """Compile `(elt for ...)`."""
    if is_async_comp(n):
        return compile_async_genexp(comp, n)
    return comprehension(comp, n, 'gen')


# -- asynchronous comprehensions -----------------------------------------------------
#
# An asynchronous list, set or dict comprehension runs inside the coroutine
# that evaluates it: it compiles to a generator-mode function (see
# generators.py) whose awaits suspend the coroutine.  An asynchronous
# generator expression is an async generator.  Each clause loops with
# `async for` or `for`; the iterables of the later clauses, the conditions
# and the element are in generator mode, so they may contain awaits.


def check_not_async(comp: Compiler, n: AnyComp) -> None:
    """An `async for` clause is a SyntaxError in a comprehension compiled
    normally (one that is not in an `async def`)."""
    for gen in n.gens:
        if gen.is_async:
            raise SyntaxError('asynchronous comprehension outside of an asynchronous function '
                              f'({comp.filename}, line {n.line})')


def compile_async_comprehension(comp: Compiler, n: ListComp | SetComp | DictComp, kind: str) -> GenFn:
    """Compile an asynchronous list, set or dict comprehension (kind 'list',
    'set' or 'dict') into a generator-mode function computing its value."""
    check_comp_yield(comp, n, kind)
    if not in_async_function(comp):
        check_not_async(comp, n)
        raise SyntaxError(f"'await' outside async function ({comp.filename}, line {n.line})")
    first: GenFn = gen_expr(comp, n.gens[0].iter)
    new_frame: Callable[[Frame], Frame] = NEW_FRAME[comp.closure_mode()]
    run: AsyncLoopFn = compile_async_loops(comp, n, kind, first)
    return make_async_comp(first, new_frame, run, ASYNC_RESULTS[kind])


def compile_async_genexp(comp: Compiler, n: GeneratorExp) -> ExprFn:
    """Compile an asynchronous generator expression: it evaluates to an
    async generator."""
    check_comp_yield(comp, n, 'gen')
    first: ExprFn = comp.expr(n.gens[0].iter)
    new_frame: Callable[[Frame], Frame] = NEW_FRAME[comp.closure_mode()]
    run: AsyncLoopFn = compile_async_loops(comp, n, 'gen', make_plain(first))
    return make_async_genexp(first, n.gens[0].is_async, new_frame, run)


ASYNC_RESULTS: dict[str, Callable[[], Any]] = {'list': list, 'set': set, 'dict': dict}
"""The type of the result of each kind of asynchronous comprehension."""


def compile_async_loops(comp: Compiler, n: AnyComp, kind: str, first: GenFn) -> AsyncLoopFn:
    """Compile the clauses and the element of an asynchronous comprehension
    (in its own scope); first is its first iterable, which the enclosing
    scope evaluates."""
    assigned: set[str] = set()
    for gen in n.gens:
        collect_target_names(gen.target, assigned)
    comp.stack.append(comprehension_scope(assigned, COMP_NAMES[kind]))
    loops: list[AsyncClause] = []
    for i, gen in enumerate(n.gens):
        itg: GenFn = gen_expr(comp, gen.iter) if i > 0 else first
        loops.append((target(comp, gen.target), itg, [gen_expr(comp, c) for c in gen.ifs], gen.is_async))
    emit: EmitFn = compile_emit(comp, n, kind)
    comp.stack.pop()
    return make_async_loops(loops, emit)


def compile_emit(comp: Compiler, n: AnyComp, kind: str) -> EmitFn:
    """Compile what an asynchronous comprehension does with each element."""
    if isinstance(n, DictComp):
        return make_emit_item(gen_expr(comp, n.key), gen_expr(comp, n.value))
    eg: GenFn = gen_expr(comp, n.elt)
    if kind == 'gen':
        return make_emit_yield(eg)
    if kind == 'set':
        return make_emit_add(eg)
    return make_emit_append(eg)


def make_emit_append(eg: GenFn) -> EmitFn:
    """`[elt ...]`: append the element to the list."""
    def emit_append(cfr: Frame, out: list[Any]) -> Generator[Any, Any, Any]:
        v: Any = yield from eg(cfr)
        out.append(v)
    return emit_append


def make_emit_add(eg: GenFn) -> EmitFn:
    """`{elt ...}`: add the element to the set."""
    def emit_add(cfr: Frame, out: set[Any]) -> Generator[Any, Any, Any]:
        v: Any = yield from eg(cfr)
        out.add(v)
    return emit_add


def make_emit_item(kg: GenFn, eg: GenFn) -> EmitFn:
    """`{key: value ...}`: the key is evaluated before the value."""
    def emit_item(cfr: Frame, out: dict[Any, Any]) -> Generator[Any, Any, Any]:
        k: Any = yield from kg(cfr)
        v: Any = yield from eg(cfr)
        out[k] = v
    return emit_item


def make_emit_yield(eg: GenFn) -> EmitFn:
    """`(elt ...)`: the async generator yields the element."""
    def emit_yield(cfr: Frame, out: None) -> Generator[Any, Any, Any]:
        v: Any = yield from eg(cfr)
        yield from agen_yield(v)
    return emit_yield


def make_async_loops(loops: list[AsyncClause], emit: EmitFn) -> AsyncLoopFn:
    """The function running clause i (and, nested in it, the later ones) of
    an asynchronous comprehension over the iterable `it`."""
    last: int = len(loops) - 1

    def visit(cfr: Frame, x: Any, i: int, out: Any) -> Generator[Any, Any, Any]:
        store, _itg, conds, _is_async = loops[i]
        store(cfr, x)
        for c in conds:
            ok: Any = yield from c(cfr)
            if not ok:
                return None
        if i == last:
            yield from emit(cfr, out)
            return None
        it: Any = yield from loops[i + 1][1](cfr)
        yield from run(cfr, it, i + 1, out)
        return None

    def run(cfr: Frame, it: Any, i: int, out: Any) -> Generator[Any, Any, Any]:
        if loops[i][3]:
            yield from async_clause(visit, cfr, it, i, out)
        else:
            for x in it:
                yield from visit(cfr, x, i, out)
    return run


def async_clause(visit: AsyncLoopFn, cfr: Frame, it: Any, i: int, out: Any) -> Generator[Any, Any, Any]:
    """Run `async for` clause i over the asynchronous iterable it, calling
    visit(cfr, x, i, out) for each item x."""
    ait: Any = aiter_of(it)
    while True:
        try:
            x: Any = yield from await_value(anext_awaitable(ait))
        except StopAsyncIteration:
            return None
        yield from visit(cfr, x, i, out)


def make_async_comp(first: GenFn, new_frame: Callable[[Frame], Frame], run: AsyncLoopFn,
                    result: Callable[[], Any]) -> GenFn:
    """An asynchronous list, set or dict comprehension: a generator-mode
    function returning the new list, set or dict (made by result())."""
    def async_comp(fr: Frame) -> Generator[Any, Any, Any]:
        it: Any = yield from first(fr)
        out: Any = result()
        yield from run(new_frame(fr), it, 0, out)
        return out
    return async_comp


def make_async_genexp(first: ExprFn, first_async: bool, new_frame: Callable[[Frame], Frame],
                      run: AsyncLoopFn) -> ExprFn:
    """An asynchronous generator expression.  As for any generator
    expression, the first iterable is evaluated at once."""
    def async_genexp(fr: Frame) -> Any:
        it: Any = first(fr)
        if not first_async:
            it = iter(it)
        cfr: Frame = new_frame(fr)
        return async_generator(drive(run(cfr, it, 0, None), cfr, 3))
    return async_genexp
