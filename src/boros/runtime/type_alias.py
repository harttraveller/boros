"""Type aliases: the values bound by `type X[T] = ...` statements (PEP 695).

The value of an alias is evaluated lazily, when it is first needed, so that
it may refer to names defined later (including the alias itself).  The
host's typing.TypeAliasType needs its value when it is created, so boros
has a class of its own that behaves like it; its type parameters are the
host's TypeVar, TypeVarTuple and ParamSpec objects.
"""

from __future__ import annotations

import types
import typing
from typing import Any

from .calls import call


class TypeAliasType:
    """The value of a `type X[params] = value` statement.  `compute` is a
    function of the type parameters that evaluates the value; it is called
    on the first access of `__value__`."""

    def __init__(self, name: str, type_params: tuple[Any, ...], compute: Any) -> None:
        self.__name__: str = name
        self.__type_params__: tuple[Any, ...] = type_params
        self.compute: Any = compute
        self.evaluated: bool = False
        self.value: Any = None

    @property
    def __value__(self) -> Any:
        """The value of the alias, evaluated on first access."""
        if not self.evaluated:
            self.value = call(self.compute, self.__type_params__, None)
            self.evaluated = True
        return self.value

    def __repr__(self) -> str:
        return self.__name__

    def __getitem__(self, args: Any) -> Any:
        """A generic alias such as Pair[int]."""
        if type(args) is not tuple:
            args = (args,)
        origin: Any = self
        return types.GenericAlias(origin, args)

    def __or__(self, other: Any) -> Any:
        """The union `alias | other`, as typing.Union[alias, other]."""
        union: Any = typing.Union
        return union[self, other]

    def __ror__(self, other: Any) -> Any:
        """The union `other | alias`."""
        union: Any = typing.Union
        return union[other, self]


TYPE_PARAM_CLASSES: dict[str, Any] = {'': typing.TypeVar, '*': typing.TypeVarTuple, '**': typing.ParamSpec}
"""The host classes of the type parameters of an alias, by kind."""


def make_type_alias(name: str, params: list[tuple[str, str]], compute: Any) -> TypeAliasType:
    """Create the type alias `name` with the type parameters `params`
    ((kind, name) pairs, see syntax.TypeAlias), whose value `compute`
    evaluates when called with the type parameters."""
    type_params: list[Any] = []
    for kind, pname in params:
        cls: Any = TYPE_PARAM_CLASSES[kind]
        type_params.append(cls(pname) if kind == '*' else cls(pname, infer_variance=True))
    return TypeAliasType(name, tuple(type_params), compute)
