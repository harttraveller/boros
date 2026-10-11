"""Closures that load, store and delete variables.

Every variable access is resolved at compile time (see `Compiler.resolve`),
so each closure built here does exactly one kind of lookup:

- locals and parameters: `fr[name]` in the current frame dict;
- globals: the module's globals dict, then the builtins;
- free variables: follow `depth` '.up' links to the frame of the enclosing
  function that owns the variable, then `[name]`;
- class bodies: the class namespace first, then the outer resolution.

A missing key means the variable is unbound and is turned into the same
UnboundLocalError or NameError that CPython raises.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..runtime.builtin_functions import builtins_of, global_fallback
from ..runtime.errors import unbound_free, unbound_local
from .scopes import CLASSNS, FREE, GLOBAL, LOCAL, MAPPED

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core_types import ExprFn, Frame, StmtFn, StoreFn
    from ..runtime.objects import Signal
    from ..syntax import Const, Name, Temp
    from .compiler import Compiler


# -- loading -------------------------------------------------------------------

def load_name(comp: Compiler, name: str) -> ExprFn:
    """Compile a read of variable `name` in the current scope."""
    kind, depth = comp.resolve(name)
    if kind is LOCAL:
        if comp.is_param(name):
            return make_load_param(name)
        return make_load_local(name)
    if kind is GLOBAL:
        if name == '__class__':
            fdepth: int | None = comp.function_depth()
            if fdepth is not None:
                return load_class_cell(fdepth)
        return load_global(comp, name)
    if kind is FREE:
        return load_free(comp, name, depth)
    if kind is MAPPED:
        return make_load_mapped(name, depth, load_global(comp, name))
    return load_classns(comp, name, depth)


def make_load_param(name: str) -> ExprFn:
    """Read a parameter: it is always bound, so no unbound check is needed."""
    def load_param(fr: Frame) -> Any:
        return fr[name]
    return load_param


def make_load_local(name: str) -> ExprFn:
    """Read a local variable, raising UnboundLocalError if it is unbound."""
    def load_local(fr: Frame) -> Any:
        try:
            return fr[name]
        except KeyError:
            raise unbound_local(name) from None
    return load_local


def load_global(comp: Compiler, name: str) -> ExprFn:
    """Read a global variable: the module's globals, then the builtins."""
    g: Frame = comp.g
    b: dict[str, Any] = builtins_of(g)

    def load_global_name(fr: Frame) -> Any:
        if name in g:
            return g[name]
        if name in b:
            return b[name]
        return global_fallback(name, g, b)
    return load_global_name


def load_free(comp: Compiler, name: str, depth: int) -> ExprFn:
    """Read a free variable owned by the function `depth` frames up.  The
    common depths 1 and 2 get closures with the links unrolled."""
    if depth == 1:
        return make_load_free1(name)
    if depth == 2:
        return make_load_free2(name)
    return make_load_free_n(name, depth)


def make_load_free1(name: str) -> ExprFn:
    """Read a variable of the directly enclosing function."""
    def load_free1(fr: Frame) -> Any:
        try:
            return fr['.up'][name]
        except KeyError:
            raise unbound_free(name) from None
    return load_free1


def make_load_free2(name: str) -> ExprFn:
    """Read a variable of the function two frames up."""
    def load_free2(fr: Frame) -> Any:
        try:
            return fr['.up']['.up'][name]
        except KeyError:
            raise unbound_free(name) from None
    return load_free2


def make_load_free_n(name: str, depth: int) -> ExprFn:
    """Read a variable of the function `depth` frames up."""
    def load_free(fr: Frame) -> Any:
        f: Frame = fr
        i: int = 0
        while i < depth:
            f = f['.up']
            i += 1
        try:
            return f[name]
        except KeyError:
            raise unbound_free(name) from None
    return load_free


def make_load_mapped(name: str, depth: int, fallback: ExprFn) -> ExprFn:
    """Read a name, in a comprehension in exec()/eval() code, from the locals
    mapping `depth` frames up, then globally (`fallback`).  As for any
    mapping of names, only __getitem__ is used."""
    def load_mapped(fr: Frame) -> Any:
        f: Any = fr
        i: int = 0
        while i < depth:
            f = f['.up']
            i += 1
        try:
            return f[name]
        except KeyError:
            return fallback(fr)
    return load_mapped


def make_load_mapping(name: str, fallback: ExprFn) -> ExprFn:
    """Read a name in exec()/eval() code whose locals mapping (the frame) is
    not a dict: like LOAD_NAME, only its __getitem__ is used, so that
    __missing__ and mappings without __contains__ work."""
    def load_mapping(fr: Frame) -> Any:
        try:
            return fr[name]
        except KeyError:
            return fallback(fr)
    return load_mapping


def load_classns(comp: Compiler, name: str, outer: tuple[Signal, Any]) -> ExprFn:
    """Read a name in a class body: the class namespace (the frame) first,
    then wherever the name resolves outside the class (`outer`)."""
    outer_kind, outer_depth = outer
    fallback: ExprFn
    if outer_kind is GLOBAL:
        fallback = load_global(comp, name)
    else:
        fallback = load_free(comp, name, outer_depth)
    if comp.stack[-1].mapping:
        return make_load_mapping(name, fallback)

    def load_classns(fr: Frame) -> Any:
        if name in fr:
            return fr[name]
        return fallback(fr)
    return load_classns


def load_class_cell(depth: int) -> ExprFn:
    """Read the implicit `__class__` variable of a method: the class being
    defined, kept in a one-element cell stored under '.cls' in the frame of
    the method `depth` frames up (filled in once the class object exists)."""
    def load_class(fr: Frame) -> Any:
        f: Frame = fr
        i: int = 0
        while i < depth:
            f = f['.up']
            i += 1
        cell: list[Any] | None = f.get('.cls')
        if cell is None or cell[0] is None:
            raise NameError("__class__ cell not found")
        return cell[0]
    return load_class


# -- storing and deleting -----------------------------------------------------------

def store_name(comp: Compiler, name: str) -> StoreFn:
    """Compile an assignment to variable `name`: a function store(fr, value)."""
    kind, depth = comp.resolve(name)
    if kind is LOCAL or kind is CLASSNS:
        return make_store_local(name)
    if kind is GLOBAL:
        return make_store_global(comp.g, name)
    return make_store_free(name, depth)


def make_store_local(name: str) -> StoreFn:
    """Store into the current frame (a function frame or class namespace)."""
    def store_local(fr: Frame, v: Any) -> None:
        fr[name] = v
    return store_local


def make_store_global(g: Frame, name: str) -> StoreFn:
    """Store into the module's globals dict `g`."""
    def store_global(fr: Frame, v: Any) -> None:
        g[name] = v
    return store_global


def make_store_free(name: str, depth: int) -> StoreFn:
    """Store into the frame of the enclosing function `depth` frames up
    (a `nonlocal` variable)."""
    def store_free(fr: Frame, v: Any) -> None:
        f: Frame = fr
        i: int = 0
        while i < depth:
            f = f['.up']
            i += 1
        f[name] = v
    return store_free


def frame_getter(comp: Compiler, name: str) -> Callable[[Frame], Frame] | None:
    """A function returning the dict that holds variable `name`, or None when
    that dict is the current frame itself."""
    kind, depth = comp.resolve(name)
    if kind is LOCAL or kind is CLASSNS:
        return None
    if kind is GLOBAL:
        g: Frame = comp.g
        return lambda fr: g

    def get(fr: Frame) -> Frame:
        f: Frame = fr
        i: int = 0
        while i < depth:
            f = f['.up']
            i += 1
        return f
    return get


def del_name(comp: Compiler, name: str) -> StmtFn:
    """Compile `del name`, which fails if the variable is unbound."""
    get: Callable[[Frame], Frame] | None = frame_getter(comp, name)
    kind: Signal = comp.resolve(name)[0]

    def delete(fr: Frame) -> None:
        d: Frame = fr if get is None else get(fr)
        if name not in d:
            if kind is LOCAL:
                raise unbound_local(name)
            raise NameError(f"name '{name}' is not defined", name=name)
        del d[name]
    return delete


def unbind_name(comp: Compiler, name: str) -> Callable[[Frame], None]:
    """Compile a silent unbinding of `name` (no error if it is unbound), as
    done at the end of an `except ... as name:` handler."""
    get: Callable[[Frame], Frame] | None = frame_getter(comp, name)

    def unbind(fr: Frame) -> None:
        d: Frame = fr if get is None else get(fr)
        d.pop(name, None)
    return unbind


# -- expression nodes ------------------------------------------------------------

def compile_name(comp: Compiler, n: Name) -> ExprFn:
    """Compile a Name expression (a variable read)."""
    return load_name(comp, n.id)


def compile_const(comp: Compiler, n: Const) -> ExprFn:
    """Compile a constant: the closure returns the value itself."""
    v: Any = n.value

    def const(fr: Frame) -> Any:
        return v
    return const


def compile_temp(comp: Compiler, n: Temp) -> ExprFn:
    """Compile a read of a temporary frame slot made by the generator-mode
    compiler (see Compiler.new_temp)."""
    key: str = n.key

    def temp(fr: Frame) -> Any:
        return fr[key]
    return temp
