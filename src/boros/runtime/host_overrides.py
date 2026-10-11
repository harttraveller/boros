"""Replacements for host library functions that cannot work on interpreted
classes, which programs get in place of the originals.

modules.HOST_OVERRIDES lists, for a host module, the names defined here;
importing that module gives the program a copy of it in which those names
are replaced (this module is loaded only then).
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any

from .attributes import class_setattr
from .lookup import K_MISSING, K_NODICT, lookup
from .objects import MISSING, Class, Instance
from .protocols import call_special

if TYPE_CHECKING:
    from collections.abc import Callable


# -- functools.total_ordering ---------------------------------------------------

TOTAL_ORDER: dict[str, list[tuple[str, str]]] = {
    '__lt__': [('__gt__', 'not-and-ne'), ('__le__', 'or-eq'), ('__ge__', 'not')],
    '__le__': [('__ge__', 'not-or-eq'), ('__lt__', 'and-ne'), ('__gt__', 'not')],
    '__gt__': [('__lt__', 'not-and-ne'), ('__ge__', 'or-eq'), ('__le__', 'not')],
    '__ge__': [('__le__', 'not-or-eq'), ('__gt__', 'and-ne'), ('__lt__', 'not')],
}
"""For each comparison that total_ordering can start from, the comparisons
it derives from it and how (see ORDER_FORMULAS), as in functools."""

ORDER_FORMULAS: dict[str, Callable[[Any, Any, Any], Any]] = {
    'not-and-ne': lambda r, a, b: not r and a != b,
    'or-eq': lambda r, a, b: r or a == b,
    'not': lambda r, a, b: not r,
    'not-or-eq': lambda r, a, b: not r or a == b,
    'and-ne': lambda r, a, b: r and a != b,
}
"""How a derived comparison of a and b follows from the result r of the root one."""


def total_ordering(cls: Any) -> Any:
    """functools.total_ordering, also for interpreted classes (the host's
    cannot see their namespaces): given at least one of __lt__, __le__,
    __gt__ and __ge__, add the missing ones."""
    if type(cls) is not Class:
        return functools.total_ordering(cls)
    roots: list[str] = [op for op in TOTAL_ORDER if defines_order(cls, op)]
    if not roots:
        raise ValueError('must define at least one ordering operation: < > <= >=')
    root: str = max(roots)
    for opname, formula in TOTAL_ORDER[root]:
        if opname not in roots:
            class_setattr(cls, opname, derived_order(opname, root, ORDER_FORMULAS[formula]))
    return cls


def defines_order(cls: Class, op: str) -> bool:
    """Whether class cls (or a base other than object) defines comparison op."""
    e: Any = lookup(cls, op)
    return e[0] is not K_MISSING and e[0] is not K_NODICT and e[2] is not object


def derived_order(name: str, root: str, formula: Callable[[Any, Any, Any], Any]) -> Callable[[Any, Any], Any]:
    """The comparison method `name` that total_ordering derives from `root`."""
    def compare(self: Any, other: Any) -> Any:
        if type(self) is Instance:
            r: Any = call_special(self, root, (other,))
        else:
            r = getattr(type(self), root)(self, other)
        if r is MISSING or r is NotImplemented:
            return NotImplemented
        return formula(r, self, other)
    compare.__name__ = name
    return compare
