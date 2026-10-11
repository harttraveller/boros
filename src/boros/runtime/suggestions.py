"""The "Did you mean ...?" suggestions of Python 3.13's error messages.

CPython offers the closest name, by a weighted Levenshtein distance
(Python/suggestions.c), for an unexpected keyword argument (among the
function's parameter names) and, when it prints an uncaught NameError,
among the names visible in the frame that raised it.  An uncaught
NameError for the name of a standard-library module also suggests the
missing import.
"""

from __future__ import annotations

import builtins as host_builtins
import contextlib
import sys
from typing import TYPE_CHECKING, Any

from .errors import LEVEL, TB_KEY

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ..core_types import Frame

GLOBALS_KEY: str = '_boros_globals_' + LEVEL
"""The attribute of a NameError for a missing global name that holds the
module's globals, among which the traceback looks for a suggestion."""

MOVE_COST: int = 2
"""The cost of inserting, deleting or replacing a character."""

CASE_COST: int = 1
"""The cost of replacing a character by the same letter in another case."""

MAX_STRING: int = 40
"""Longer names (after removing a common prefix and suffix) are never close."""

MAX_ITEMS: int = 750
"""With this many candidates or more, no suggestion is made."""


# -- distances -----------------------------------------------------------------

def trim_common(a: str, b: str) -> tuple[str, str]:
    """a and b without their common prefix and suffix."""
    pre: int = 0
    while pre < len(a) and pre < len(b) and a[pre] == b[pre]:
        pre += 1
    a = a[pre:]
    b = b[pre:]
    while a and b and a[-1] == b[-1]:
        a = a[:-1]
        b = b[:-1]
    return a, b


def substitution_cost(x: str, y: str) -> int:
    """The cost of replacing character x by character y."""
    if x == y:
        return 0
    if x.lower() == y.lower():
        return CASE_COST
    return MOVE_COST


def edit_distance(a: str, b: str, max_cost: int) -> int:
    """The weighted edit distance of a and b (len(a) <= len(b)), computed
    row by row; max_cost + 1 as soon as it must exceed max_cost."""
    row: list[int] = list(range(MOVE_COST, MOVE_COST * (len(a) + 1), MOVE_COST))
    result: int = 0
    for bindex in range(len(b)):
        bchar: str = b[bindex]
        distance: int = bindex * MOVE_COST
        result = distance
        minimum: int = max_cost + 1
        for index in range(len(a)):
            substitute: int = distance + substitution_cost(a[index], bchar)
            distance = row[index]
            result = min(min(result, distance) + MOVE_COST, substitute)
            row[index] = result
            minimum = min(minimum, result)
        if minimum > max_cost:
            return max_cost + 1
    return result


def levenshtein(a: str, b: str, max_cost: int) -> int:
    """The distance between names a and b, or max_cost + 1 if it is larger."""
    if a == b:
        return 0
    a, b = trim_common(a, b)
    if not a or not b:
        return MOVE_COST * (len(a) + len(b))
    if len(a) > MAX_STRING or len(b) > MAX_STRING:
        return max_cost + 1
    if len(b) < len(a):
        a, b = b, a
    if (len(b) - len(a)) * MOVE_COST > max_cost:
        return max_cost + 1
    return edit_distance(a, b, max_cost)


def suggest_name(name: str, candidates: list[Any]) -> str | None:
    """The candidate closest to name (the first of equally close ones), or
    None if none is close enough: at most a third of the characters may
    need changing."""
    if len(candidates) >= MAX_ITEMS:
        return None
    best: str | None = None
    best_distance: int = 0
    for item in candidates:
        if type(item) is not str or item == name:
            continue
        max_distance: int = (len(name) + len(item) + 3) * MOVE_COST // 6
        if best is not None and best_distance - 1 < max_distance:
            max_distance = best_distance - 1
        d: int = levenshtein(name, item, max_distance)
        if d <= max_distance and (best is None or d < best_distance):
            best = item
            best_distance = d
    return best


# -- uncaught NameErrors -------------------------------------------------------

def visible_names(fr: Frame, g: Frame) -> list[Any]:
    """The names visible in frame fr of a module with globals g, in the
    order CPython considers them: locals, globals, builtins (at module level
    the globals are the locals too, and count twice)."""
    names: list[Any] = [k for k in fr if type(k) is str and k[:1] != '.']
    names.extend(g)
    names.extend(host_builtins.__dict__)
    return names


def self_suggestion(fr: Frame, g: Frame, name: str) -> str | None:
    """'self.name' if the failing code is a method whose `self` has an
    attribute `name`."""
    if fr is g or 'self' not in fr:
        return None
    from .attributes import getattr_any
    with contextlib.suppress(Exception):
        getattr_any(fr['self'], name)
        return 'self.' + name
    return None


def frame_suggestion(e: BaseException, name: str) -> str | None:
    """The suggestion for NameError e about `name`, from the innermost frame
    of its interpreted traceback (None if there is none)."""
    tb: list[Any] | None = getattr(e, TB_KEY, None)
    g: Frame | None = getattr(e, GLOBALS_KEY, None)
    if not tb or g is None:
        return None
    fr: Frame = tb[0][0]
    suggestion: str | None = self_suggestion(fr, g, name)
    if suggestion is None:
        suggestion = suggest_name(name, visible_names(fr, g))
    return suggestion


def name_error_hint(e: BaseException, v: Any) -> str:
    """What CPython appends to the final traceback line of an uncaught
    NameError e (whose interpreted value is v), such as
    ". Did you mean: 'total'?"; '' for other exceptions."""
    if not isinstance(v, NameError):
        return ''
    name: Any = getattr(v, 'name', None)
    if type(name) is not str:
        return ''
    hint: str = ''
    suggestion: str | None = frame_suggestion(e, name)
    if suggestion is not None:
        hint = f". Did you mean: '{suggestion}'?"
    if name in sys.stdlib_module_names:
        if hint:
            hint += f" Or did you forget to import '{name}'?"
        else:
            hint = f". Did you forget to import '{name}'?"
    return hint


def keyword_suggestion(name: str, params: Iterable[str]) -> str:
    """The " Did you mean 'x'?" suffix for an unexpected keyword argument
    `name`, given the names that may be passed by keyword ('' if none is
    close)."""
    suggestion: str | None = suggest_name(name, list(params))
    if suggestion is None:
        return ''
    return f". Did you mean '{suggestion}'?"
