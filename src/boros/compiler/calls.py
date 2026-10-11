"""Compilation of calls, with inlined fast paths for calls between closures.

A call `f(a, b)` compiles to a closure that evaluates the callee and the
arguments and then calls.  Calling an interpreted Function means binding its
parameters into a fresh frame dict and running its body closure; the general
runtime `invoke` does that for any signature.  For the shapes that dominate
real programs the closures here do it inline instead:

* one or two positional arguments to a Function whose parameters are just
  as many plain names (`f.p1` / `f.p2` are set for those): the new frame is
  built directly, skipping `invoke` altogether;
* `obj.method(...)` on an interpreted instance whose class supplies the
  method as a plain function (the attribute cache says K_FUNC): the function
  is invoked with `obj` prepended, without creating a bound Method object;
* `f(param)` where `f` is a simple name and the argument a parameter of the
  current function, which is how the interpreter's own closures call each
  other (`body(fr)`), so it matters most when boros runs itself.

Calls with keywords or `*args`/`**kwargs` take the general path, and a few
builtins (`super`, `locals`, `eval`, ...) that need the caller's frame are
handled as intrinsics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..runtime.attributes import getattr_any, inst_getattr
from ..runtime.builtin_functions import (
    BUILTINS,
    b_dir,
    b_eval,
    b_exec,
    b_globals,
    b_locals,
    b_vars,
    builtins_of,
    global_fallback,
)
from ..runtime.calls import call, invoke
from ..runtime.coroutines import EXC_ARG_METHODS, native_exc_args
from ..runtime.errors import annotate_call, unbound_free, unbound_local
from ..runtime.exceptions import SPECIAL_ATTRS
from ..runtime.lookup import K_FUNC
from ..runtime.objects import Function, Instance, Method, Super
from ..runtime.typechecks import STANDIN_TYPES, is_iterable_type, standin_type, type_name
from ..syntax import Attribute, Name, Starred
from .expressions import sequence_items
from .scopes import CLASSNS, GLOBAL

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core_types import Args, ExprFn, Frame, Kwargs
    from ..runtime.objects import Signal
    from ..syntax import Call, Expression, Scope
    from .compiler import Compiler

    # Evaluates the callee and the arguments of a general call into
    # (callee, args, kwargs).
    PartsFn = Callable[[Frame], tuple[Any, Args, Kwargs]]

# Builtins that are compiled specially when called by name.
INTRINSICS: dict[str, int] = {'locals': 1, 'globals': 1, 'vars': 1, 'dir': 1, 'eval': 1, 'exec': 1, 'super': 1}


def frame_locals(fr: Frame) -> dict[str, Any]:
    """The user-visible variables of a frame (bookkeeping keys start with '.')."""
    out: dict[str, Any] = {}
    for k in fr:
        if k[0] != '.':
            out[k] = fr[k]
    return out


def add_free_variables(out: dict[str, Any], fr: Frame, freevars: dict[str, int]) -> None:
    """Add to out the bound free variables of the function whose frame is
    fr: each of freevars is that many '.up' links away."""
    for name, depth in freevars.items():
        if name not in out:
            f: Frame = fr
            i: int = depth
            while i > 0:
                f = f['.up']
                i -= 1
            if name in f:
                out[name] = f[name]


def locals_snapshot(fr: Frame, freevars: dict[str, int], inline_up: int) -> dict[str, Any]:
    """locals() in a function (PEP 667): a new dict of the variables of the
    function's frame and of the free variables it uses.  In a comprehension
    inlined into the function (PEP 709), fr is the comprehension's frame,
    `inline_up` links below the function's, and the variables of the
    comprehensions are included too."""
    frames: list[Frame] = [fr]
    f: Frame = fr
    i: int = 0
    while i < inline_up:
        f = f['.up']
        frames.append(f)
        i += 1
    out: dict[str, Any] = frame_locals(f)
    add_free_variables(out, f, freevars)
    i = inline_up - 1
    while i >= 0:
        out.update(frame_locals(frames[i]))
        i -= 1
    return out


def namespace_locals(fr: Frame) -> Frame:
    """locals() in a class body: the class namespace itself."""
    return fr


def make_snapshot(freevars: dict[str, int], inline_up: int) -> Callable[[Frame], Frame]:
    """locals() for code in a function (see locals_snapshot)."""
    def snapshot(fr: Frame) -> Frame:
        return locals_snapshot(fr, freevars, inline_up)
    return snapshot


def local_names(comp: Compiler, mode: int) -> Callable[[Frame], Frame]:
    """How locals(), and the default locals of eval() and exec(), are made
    for the code being compiled (mode is its Compiler.closure_mode): the
    namespace itself in a class body, else a snapshot of the function's
    variables, to which an inlined comprehension adds its own."""
    if mode != 0:
        return namespace_locals
    stack: list[Scope] = comp.stack
    top: int = len(stack) - 1
    j: int = top
    while j > 0 and stack[j].inlined:
        j -= 1
    if stack[j].kind == 'module' or stack[j].kind == 'class':
        # a comprehension at module level or in a class body: its own frame
        j = top
    return make_snapshot(stack[j].freevars, top - j)


def compile_call(comp: Compiler, n: Call) -> ExprFn:
    """Compile a call expression, choosing the cheapest calling closure."""
    func: Expression = n.func
    if type(func) is Name and func.id in INTRINSICS and is_global_name(comp, func.id):
        return intrinsic_call(comp, n, func.id)
    if not is_simple_call(n):
        return general_call(comp, n)
    if type(func) is Attribute and func.attr not in SPECIAL_ATTRS:
        return method_call(comp, func, [comp.expr(a) for a in n.args], n.args)
    if type(func) is Name and func.id == 'type' and len(n.args) == 1 and is_global_name(comp, 'type'):
        return make_type_call(comp.g, comp.expr(n.args[0]))
    return positional_call(comp, func, n.args)


def make_type_call(g: Frame, ac: ExprFn) -> ExprFn:
    """`type(x)` where `type` is the builtin (unless the program rebinds it).

    The interpreter's own code asks for `type(o)` constantly, so when boros
    runs itself this saves a call through call() at every level."""
    b: dict[str, Any] = BUILTINS

    def type_call(fr: Frame) -> Any:
        f: Any = g['type'] if 'type' in g else b['type']
        a: Any = ac(fr)
        if f is type:
            t: Any = type(a)
            if t is Instance:
                return a.cls
            if t in STANDIN_TYPES:
                return standin_type(a)
            return t
        return call(f, (a,), None)
    return type_call


def is_global_name(comp: Compiler, name: str) -> bool:
    """Whether `name` resolves to the module globals (and so, unless the
    module rebinds it, to the builtin of that name)."""
    res: tuple[Signal, Any] = comp.resolve(name)
    return res[0] is GLOBAL or (res[0] is CLASSNS and res[1][0] is GLOBAL)


def is_simple_call(n: Call) -> bool:
    """Whether a call passes only plain positional arguments."""
    if n.keywords:
        return False
    for a in n.args:
        if type(a) is Starred:
            return False
    return True


# -- plain positional calls --------------------------------------------------------

def positional_call(comp: Compiler, func: Expression, args: list[Expression]) -> ExprFn:
    """`f(a, b, ...)` with only positional arguments and a callee that is not
    an attribute."""
    nargs: int = len(args)
    fk, _ = comp.operand(func)
    if nargs == 1 and fk is not None and type(func) is Name:
        aname: str | None = comp.local_name(args[0])
        if aname is not None and comp.is_param(aname):
            return call1_inline(comp, fk, func.id, aname)
    argcs: list[ExprFn] = [comp.expr(a) for a in args]
    fc: ExprFn = comp.expr(func)
    if nargs == 0:
        return make_call0(fc)
    if nargs == 1:
        return make_call1(fc, argcs[0])
    if nargs == 2:
        return make_call2(fc, argcs[0], argcs[1])
    if nargs == 3:
        return make_call3(fc, argcs[0], argcs[1], argcs[2])
    return make_calln(fc, argcs)


def make_call0(fc: ExprFn) -> ExprFn:
    """`f()`."""

    def call0(fr: Frame) -> Any:
        f: Any = fc(fr)
        if type(f) is Function:
            return invoke(f, (), None)
        return call(f, (), None)
    return call0


def make_call1(fc: ExprFn, a0: ExprFn) -> ExprFn:
    """`f(a)`: a Function with one plain parameter gets its frame built inline."""

    def call1(fr: Frame) -> Any:
        f: Any = fc(fr)
        a: Any = a0(fr)
        if type(f) is Function:
            n1: str | None = f.p1
            if n1 is not None:
                nfr: Frame = {n1: a, '.up': f.closure}
                try:
                    return f.body(nfr)
                except BaseException as e:
                    annotate_call(e, nfr, f)
                    raise
            return invoke(f, (a,), None)
        return call(f, (a,), None)
    return call1


def make_call2(fc: ExprFn, a0: ExprFn, a1: ExprFn) -> ExprFn:
    """`f(a, b)`: a Function with two plain parameters gets its frame built inline."""

    def call2(fr: Frame) -> Any:
        f: Any = fc(fr)
        a: Any = a0(fr)
        b: Any = a1(fr)
        if type(f) is Function:
            n2: list[str] | None = f.p2
            if n2 is not None:
                nfr: Frame = {n2[0]: a, n2[1]: b, '.up': f.closure}
                try:
                    return f.body(nfr)
                except BaseException as e:
                    annotate_call(e, nfr, f)
                    raise
            return invoke(f, (a, b), None)
        return call(f, (a, b), None)
    return call2


def make_call3(fc: ExprFn, a0: ExprFn, a1: ExprFn, a2: ExprFn) -> ExprFn:
    """`f(a, b, c)`."""

    def call3(fr: Frame) -> Any:
        f: Any = fc(fr)
        args: Args = (a0(fr), a1(fr), a2(fr))
        if type(f) is Function:
            return invoke(f, args, None)
        return call(f, args, None)
    return call3


def make_calln(fc: ExprFn, argcs: list[ExprFn]) -> ExprFn:
    """`f(a, b, c, d, ...)`."""

    def calln(fr: Frame) -> Any:
        f: Any = fc(fr)
        args: Args = tuple([a(fr) for a in argcs])
        if type(f) is Function:
            return invoke(f, args, None)
        return call(f, args, None)
    return calln


# -- f(param) where f is a simple name ------------------------------------------------

def call1_inline(comp: Compiler, fk: str, fname: str, aname: str) -> ExprFn:
    """A one-argument call whose callee is a simple name and whose
    argument is a parameter (the shape of nearly every call between the
    interpreter's own closures, e.g. `body(fr)`).  Both the callee and the
    argument are read straight from the frames; fk is the callee's operand
    kind ('free1', 'global', 'param' or 'local')."""
    if fk == 'free1':
        return make_call1_free(fname, aname)
    if fk == 'global':
        return make_call1_global(comp.g, builtins_of(comp.g), fname, aname)
    if fk == 'param':
        return make_call1_param(fname, aname)
    return make_call1_local(fname, aname)


def make_call1_free(fname: str, aname: str) -> ExprFn:
    """`f(param)` where f is a variable of the directly enclosing function."""

    def call1_free(fr: Frame) -> Any:
        try:
            f: Any = fr['.up'][fname]
        except KeyError:
            raise unbound_free(fname) from None
        a: Any = fr[aname]
        if type(f) is Function:
            n1: str | None = f.p1
            if n1 is not None:
                nfr: Frame = {n1: a, '.up': f.closure}
                try:
                    return f.body(nfr)
                except BaseException as e:
                    annotate_call(e, nfr, f)
                    raise
            return invoke(f, (a,), None)
        return call(f, (a,), None)
    return call1_free


def make_call1_global(g: Frame, b: dict[str, Any], fname: str, aname: str) -> ExprFn:
    """`f(param)` where f is a global (or builtin) name; g is the module
    globals and b the builtins."""

    def call1_global(fr: Frame) -> Any:
        if fname in g:
            f: Any = g[fname]
        elif fname in b:
            f = b[fname]
        else:
            f = global_fallback(fname, g, b)
        a: Any = fr[aname]
        if type(f) is Function:
            n1: str | None = f.p1
            if n1 is not None:
                nfr: Frame = {n1: a, '.up': f.closure}
                try:
                    return f.body(nfr)
                except BaseException as e:
                    annotate_call(e, nfr, f)
                    raise
            return invoke(f, (a,), None)
        return call(f, (a,), None)
    return call1_global


def make_call1_param(fname: str, aname: str) -> ExprFn:
    """`f(param)` where f is itself a parameter."""

    def call1_param(fr: Frame) -> Any:
        f: Any = fr[fname]
        a: Any = fr[aname]
        if type(f) is Function:
            n1: str | None = f.p1
            if n1 is not None:
                nfr: Frame = {n1: a, '.up': f.closure}
                try:
                    return f.body(nfr)
                except BaseException as e:
                    annotate_call(e, nfr, f)
                    raise
            return invoke(f, (a,), None)
        return call(f, (a,), None)
    return call1_param


def make_call1_local(fname: str, aname: str) -> ExprFn:
    """`f(param)` where f is a local variable, which may be unbound."""

    def call1_local(fr: Frame) -> Any:
        try:
            f: Any = fr[fname]
        except KeyError:
            raise unbound_local(fname) from None
        a: Any = fr[aname]
        if type(f) is Function:
            n1: str | None = f.p1
            if n1 is not None:
                nfr: Frame = {n1: a, '.up': f.closure}
                try:
                    return f.body(nfr)
                except BaseException as e:
                    annotate_call(e, nfr, f)
                    raise
            return invoke(f, (a,), None)
        return call(f, (a,), None)
    return call1_local


# -- method calls ----------------------------------------------------------------------
#
# `o.name(args)` on an interpreted instance whose class provides `name` as a
# plain function (cache entry kind K_FUNC) and whose instance dict does not
# shadow it is the classic method call: invoke the function with `o` as the
# first argument.  Anything else fetches the attribute and calls the result.

def method_call(comp: Compiler, func: Attribute, argcs: list[ExprFn],
                argnodes: list[Expression] | None = None) -> ExprFn:
    """Compile `obj.name(args)` with positional arguments only, given the
    compiled argument closures (argnodes, the argument nodes, is unused)."""
    oc: ExprFn = comp.expr(func.value)
    name: str = func.attr
    nargs: int = len(argcs)
    if name in EXC_ARG_METHODS:
        return make_exc_mcall(oc, name, argcs)
    if nargs == 0:
        return make_mcall0(oc, name)
    if nargs == 1:
        return make_mcall1(oc, name, argcs[0])
    if nargs == 2:
        return make_mcall2(oc, name, argcs[0], argcs[1])
    return make_mcalln(oc, name, argcs)


def make_exc_mcall(oc: ExprFn, name: str, argcs: list[ExprFn]) -> ExprFn:
    """`o.throw(exc)` or `o.set_exception(exc)`: a host generator,
    coroutine or future cannot take an interpreted exception, so it is
    given the host exception standing for it."""

    def exc_mcall(fr: Frame) -> Any:
        o: Any = oc(fr)
        if type(o) is Instance:
            m: Any = inst_getattr(o, name)
            return call(m, tuple([a(fr) for a in argcs]), None)
        m = getattr_any(o, name)
        return call(m, native_exc_args(tuple([a(fr) for a in argcs])), None)
    return exc_mcall


def make_mcall0(oc: ExprFn, name: str) -> ExprFn:
    """`o.name()`."""

    def mcall0(fr: Frame) -> Any:
        o: Any = oc(fr)
        if type(o) is Instance:
            e: tuple[Signal, Any, Any] | None = o.cls.acache.get(name)
            if e is not None and e[0] is K_FUNC and name not in o.d:
                return invoke(e[1], (o,), None)
            return call(inst_getattr(o, name), (), None)
        return call(getattr_any(o, name), (), None)
    return mcall0


def make_mcall1(oc: ExprFn, name: str, a0: ExprFn) -> ExprFn:
    """`o.name(a)`."""

    def mcall1(fr: Frame) -> Any:
        o: Any = oc(fr)
        if type(o) is Instance:
            e: tuple[Signal, Any, Any] | None = o.cls.acache.get(name)
            if e is not None and e[0] is K_FUNC and name not in o.d:
                return invoke(e[1], (o, a0(fr)), None)
            m: Any = inst_getattr(o, name)
            return call(m, (a0(fr),), None)
        m = getattr_any(o, name)
        return call(m, (a0(fr),), None)
    return mcall1


def make_mcall2(oc: ExprFn, name: str, a0: ExprFn, a1: ExprFn) -> ExprFn:
    """`o.name(a, b)`."""

    def mcall2(fr: Frame) -> Any:
        o: Any = oc(fr)
        if type(o) is Instance:
            e: tuple[Signal, Any, Any] | None = o.cls.acache.get(name)
            if e is not None and e[0] is K_FUNC and name not in o.d:
                return invoke(e[1], (o, a0(fr), a1(fr)), None)
            m: Any = inst_getattr(o, name)
            return call(m, (a0(fr), a1(fr)), None)
        m = getattr_any(o, name)
        return call(m, (a0(fr), a1(fr)), None)
    return mcall2


def make_mcalln(oc: ExprFn, name: str, argcs: list[ExprFn]) -> ExprFn:
    """`o.name(a, b, c, ...)`."""

    def mcalln(fr: Frame) -> Any:
        o: Any = oc(fr)
        if type(o) is Instance:
            e: tuple[Signal, Any, Any] | None = o.cls.acache.get(name)
            if e is not None and e[0] is K_FUNC and name not in o.d:
                args: list[Any] = [o]
                for a in argcs:
                    args.append(a(fr))
                return invoke(e[1], tuple(args), None)
            m: Any = inst_getattr(o, name)
        else:
            m = getattr_any(o, name)
        return call(m, tuple([a(fr) for a in argcs]), None)
    return mcalln


# -- general calls: *args, keywords, **kwargs -------------------------------------------

def call_parts(comp: Compiler, n: Call, fc: ExprFn) -> PartsFn:
    """Compile the callee fc and the arguments of call n into a function
    returning (callee, args, kwargs)."""
    _, pos = sequence_items(comp, n.args)
    kws: list[tuple[str | None, ExprFn]] = [(k.arg, comp.expr(k.value)) for k in n.keywords]
    return make_call_parts(fc, pos, kws)


def make_call_parts(fc: ExprFn, pos: list[tuple[bool, ExprFn]], kws: list[tuple[str | None, ExprFn]]) -> PartsFn:
    """Build the evaluator for a general call: the callee fc first, then the
    arguments.  pos pairs each positional argument with whether it is
    `*starred`; kws pairs each keyword name with its value closure, a name
    of None marking `**mapping`.  Errors in the arguments name the callee."""

    def parts(fr: Frame) -> tuple[Any, Args, Kwargs]:
        f: Any = fc(fr)
        args: list[Any] = []
        for star, c in pos:
            if star:
                v: Any = c(fr)
                try:
                    args.extend(v)
                except TypeError:
                    if is_iterable_type(v):
                        raise
                    raise TypeError(f'{func_str(f)} argument after * must be an iterable, not {type_name(v)}') from None
            else:
                args.append(c(fr))
        kw: Kwargs = None
        if kws:
            kw = {}
            for name, c in kws:
                if name is None:
                    merge_kwargs(kw, c(fr), f)
                elif name in kw:
                    raise multiple_keyword_values(f, name)
                else:
                    kw[name] = c(fr)
        return f, tuple(args), kw
    return parts


def merge_kwargs(kw: dict[str, Any], m: Any, f: Any) -> None:
    """Add the items of a `**m` argument of a call of f to the keyword
    arguments kw.  m may be any mapping (anything with keys() and indexing)."""
    if type(m) is dict:
        items: Any = m.items()
    else:
        try:
            keys: Any = m.keys()
        except AttributeError:
            raise TypeError(f'{func_str(f)} argument after ** must be a mapping, not {type_name(m)}') from None
        items = [(k, m[k]) for k in keys]
    for k, v in items:
        if type(k) is not str:
            raise TypeError('keywords must be strings')
        if k in kw:
            raise multiple_keyword_values(f, k)
        kw[k] = v


def multiple_keyword_values(f: Any, name: str) -> TypeError:
    """The error for keyword argument `name` given twice in a call of f."""
    return TypeError(f"{func_str(f)} got multiple values for keyword argument '{name}'")


def func_str(f: Any) -> str:
    """How CPython's call errors name the callee f (_PyObject_FunctionStr):
    'module.qualname()', or just 'qualname()' for builtins.  A bound method
    is named by its function."""
    if type(f) is Method:
        f = f.im_func
    try:
        qualname: Any = getattr_any(f, '__qualname__')
    except AttributeError:
        return str(f)
    try:
        module: Any = getattr_any(f, '__module__')
    except AttributeError:
        module = None
    if type(module) is str and module != 'builtins':
        return f'{module}.{qualname}()'
    return f'{qualname}()'


def general_call(comp: Compiler, n: Call) -> ExprFn:
    """Compile a call with keywords, `*args` or `**kwargs`."""
    func: Expression = n.func
    if type(func) is Attribute and func.attr not in SPECIAL_ATTRS:
        fc: ExprFn = make_getattr(comp.expr(func.value), func.attr)
    else:
        fc = comp.expr(func)
    return make_general_call(call_parts(comp, n, fc))


def make_getattr(oc: ExprFn, name: str) -> ExprFn:
    """`o.name` evaluated as the callee of a general call."""

    def fc(fr: Frame) -> Any:
        return getattr_any(oc(fr), name)
    return fc


def make_general_call(parts: PartsFn) -> ExprFn:
    """Evaluate the callee, then the arguments, then call."""

    def gcall(fr: Frame) -> Any:
        f, args, kw = parts(fr)
        return call(f, args, kw)
    return gcall


# -- intrinsics: builtins that need the caller's frame ---------------------------------
#
# `super()`, `locals()`, `vars()`, `dir()`, `eval(s)` and `exec(s)` look at
# the frame they are called from, which a builtin cannot see.  When one of
# these names is called (and resolves to the global namespace) the call
# compiles to a closure that checks, at run time, whether the callee really
# is that builtin and if so supplies the frame; otherwise it is an ordinary
# call.

def intrinsic_call(comp: Compiler, n: Call, name: str) -> ExprFn:
    """Compile a call to one of the INTRINSICS."""
    parts: PartsFn = call_parts(comp, n, comp.expr(n.func))
    if name == 'super':
        depth, first, is_vararg = super_arguments(comp)
        return make_super_call(parts, depth, first, is_vararg)
    # in exec() code with separate locals, locals() is that mapping
    mode: int = 1 if comp.stack[-1].exec_locals else comp.closure_mode()
    if mode == 1 and name != 'globals':
        # the class body runs in a namespace that locals() can return
        comp.stack[-1].uses_locals = True
    return make_intrinsic(parts, comp.g, mode, local_names(comp, mode))


def enclosing_function_scope(comp: Compiler) -> Scope | None:
    """The innermost function scope being compiled, if any."""
    for s in reversed(comp.stack):
        if s.kind == 'function':
            return s
    return None


def super_arguments(comp: Compiler) -> tuple[int | None, str | None, bool]:
    """What zero-argument `super()` needs to find its arguments at run time:
    (depth, first, is_vararg).  depth is the number of frame links from the
    current frame up to the enclosing function's frame (None outside a
    function), first the name of that function's first parameter (None if
    it has none), and is_vararg whether that parameter is `*args`, in which
    case the object is its first element."""
    depth: int | None = comp.function_depth()
    if depth is None:
        return None, None, False
    fs: Scope | None = enclosing_function_scope(comp)
    if fs is None:
        return depth, None, False
    if fs.argnames:
        return depth, fs.argnames[0], False
    if fs.vararg:
        return depth, fs.vararg, True
    return depth, None, False


def make_super_call(parts: PartsFn, depth: int | None, first: str | None, is_vararg: bool) -> ExprFn:
    """`super(...)`.  With no arguments, super's two arguments come from the
    enclosing method: the class from its `__class__` cell (kept under '.cls'
    in the function's frame) and the object from its first parameter."""

    def super_call(fr: Frame) -> Any:
        f, args, kw = parts(fr)
        if f is super and not args and not kw:
            if depth is None:
                raise RuntimeError('super(): no arguments')
            mfr: Frame = fr
            i: int = 0
            while i < depth:
                mfr = mfr['.up']
                i += 1
            cell: list[Any] | None = mfr.get('.cls')
            if cell is None or cell[0] is None:
                raise RuntimeError('super(): __class__ cell not found')
            if first is None:
                raise RuntimeError('super(): no arguments')
            if first not in mfr:
                raise RuntimeError('super(): arg[0] deleted')
            obj: Any = mfr[first]
            if is_vararg:
                if not obj:
                    raise RuntimeError('super(): no arguments')
                obj = obj[0]
            return Super(cell[0], obj)
        return call(f, args, kw)
    return super_call


def make_intrinsic(parts: PartsFn, g: Frame, mode: int, names: Callable[[Frame], Frame]) -> ExprFn:
    """`locals()`, `vars()`, `dir()`, `globals()`, `eval(s)` and `exec(s)`.
    mode is the Compiler.closure_mode of the calling code: 2 means module
    level, where the locals are the globals g; otherwise names(fr) gives
    the locals (see local_names)."""

    def intrinsic(fr: Frame) -> Any:
        f, args, kw = parts(fr)
        if f is b_locals or ((f is b_vars or f is b_dir) and not args):
            loc: dict[str, Any] = g if mode == 2 else names(fr)
            if f is b_dir:
                return sorted(loc)
            return loc
        if f is b_globals:
            return g
        if (f is b_eval or f is b_exec) and len(args) < 2 and not (kw and 'globals' in kw):
            if len(args) == 0:
                return call(f, args, kw)
            return f(args[0], g, None if mode == 2 else names(fr), own_frame=True)
        return call(f, args, kw)
    return intrinsic
