"""Introspection of interpreted functions: the parts of a function's host
interface that programs read to inspect it, and that are computed only
when asked for (objects.introspect loads this module on first use).

Programs and the standard library (inspect, typing, dataclasses, ...)
examine functions through __code__ (co_varnames, co_flags), __closure__
and __signature__.  A Function is not a host function, so these are made
here from what the compiler recorded: the parameter lists, the defaults
and annotations, and the free variables of each scope.
"""

from __future__ import annotations

from inspect import Parameter, Signature, signature
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core_types import Frame
    from .objects import Code, Function, Method


def code_varnames(code: Code) -> tuple[str, ...]:
    """co_varnames: the parameters (positional, keyword-only, *args, **kwargs)
    and then the other local variables (in sorted order; CPython uses the
    order of first appearance)."""
    names: list[str] = code.params + code.kwonly
    if code.vararg is not None:
        names.append(code.vararg)
    if code.kwarg is not None:
        names.append(code.kwarg)
    others: list[str] = sorted([n for n in code.localnames if n not in names])
    return tuple(names + others)


def code_flags(code: Code) -> int:
    """co_flags: CO_OPTIMIZED | CO_NEWLOCALS, plus CO_VARARGS, CO_VARKEYWORDS,
    CO_NESTED, and CO_GENERATOR or CO_COROUTINE."""
    flags: int = 3
    if code.vararg is not None:
        flags |= 4
    if code.kwarg is not None:
        flags |= 8
    if code.nested:
        flags |= 16
    if code.is_async:
        flags |= 128
    elif code.is_gen:
        flags |= 32
    return flags


class Cell:
    """A view of one free variable of a function, as found in __closure__:
    the variable `name` of the frame `frame` that owns it."""

    __slots__ = ('frame', 'name')

    def __init__(self, frame: Frame, name: str) -> None:
        self.frame: Frame = frame
        self.name: str = name

    def _get(self) -> Any:
        try:
            return self.frame[self.name]
        except KeyError:
            raise ValueError('Cell is empty') from None

    def _set(self, v: Any) -> None:
        self.frame[self.name] = v

    def _del(self) -> None:
        self.frame.pop(self.name, None)

    cell_contents = property(_get, _set, _del)

    def __repr__(self) -> str:
        return f'<cell at 0x{id(self):x}>'


# type(c).__name__ is 'cell', as in CPython
Cell.__name__ = 'cell'


def closure_cells(f: Function) -> tuple[Cell, ...] | None:
    """Function.__closure__: a cell for each free variable of f (sorted by
    name, like co_freevars), or None if it has none."""
    fv: dict[str, int] = f.code.freevars
    if not fv:
        return None
    cells: list[Cell] = []
    for name in sorted(fv):
        d: Any = f.closure
        i: int = 1
        while i < fv[name]:
            d = d['.up']
            i += 1
        cells.append(Cell(d, name))
    return tuple(cells)


def function_signature(f: Function) -> Any:
    """Function.__signature__: the inspect.Signature of f, built from its
    code, defaults and annotations (inspect cannot introspect a Function
    itself).  An assigned __signature__ wins, and a wrapper made with
    functools.wraps reports the signature of the function it wraps."""
    d: dict[str, Any] = f.__dict__
    if '__signature__' in d:
        return d['__signature__']
    if '__wrapped__' in d:
        return signature(d['__wrapped__'])
    anns: dict[str, Any] = f.__annotations__
    params: list[Parameter] = positional_parameters(f, anns)
    params.extend(other_parameters(f, anns))
    return Signature(params, return_annotation=anns.get('return', Signature.empty))


def positional_parameters(f: Function, anns: dict[str, Any]) -> list[Parameter]:
    """The inspect.Parameters of f's positional parameters, with their defaults."""
    code: Code = f.code
    defaults: tuple[Any, ...] = f.defaults or ()
    first_default: int = code.argcount - len(defaults)
    params: list[Parameter] = []
    for i, name in enumerate(code.params):
        kind: Any = Parameter.POSITIONAL_ONLY if i < code.nposonly else Parameter.POSITIONAL_OR_KEYWORD
        default: Any = defaults[i - first_default] if i >= first_default else Parameter.empty
        params.append(Parameter(name, kind, default=default, annotation=anns.get(name, Parameter.empty)))
    return params


def other_parameters(f: Function, anns: dict[str, Any]) -> list[Parameter]:
    """The inspect.Parameters of f's *args, keyword-only parameters and **kwargs."""
    code: Code = f.code
    empty: Any = Parameter.empty
    params: list[Parameter] = []
    if code.vararg is not None:
        params.append(Parameter(code.vararg, Parameter.VAR_POSITIONAL, annotation=anns.get(code.vararg, empty)))
    kwd: dict[str, Any] = f.kwdefaults or {}
    for name in code.kwonly:
        params.append(Parameter(name, Parameter.KEYWORD_ONLY, default=kwd.get(name, empty),
                                annotation=anns.get(name, empty)))
    if code.kwarg is not None:
        params.append(Parameter(code.kwarg, Parameter.VAR_KEYWORD, annotation=anns.get(code.kwarg, empty)))
    return params


def method_signature(m: Method) -> Any:
    """Method.__signature__: the signature of the bound function without
    its first parameter (a leading *args stays, as inspect does it)."""
    sig: Signature = signature(m.im_func)
    params: list[Parameter] = list(sig.parameters.values())
    if not params or params[0].kind is Parameter.VAR_KEYWORD or params[0].kind is Parameter.KEYWORD_ONLY:
        raise ValueError('invalid method signature')
    if params[0].kind is not Parameter.VAR_POSITIONAL:
        params = params[1:]
    return sig.replace(parameters=params)
