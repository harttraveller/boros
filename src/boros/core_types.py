"""Type aliases shared across the interpreter.

Interpreted values are ordinary Python objects of any type, so they are
annotated as `Any`.  Compiled code is represented by closures over a frame.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .runtime.objects import Signal

Frame = dict[str, Any]
"""The local variables of one function call (or a class body, or a module's
globals).  Keys starting with '.' hold interpreter bookkeeping."""

ExprFn = Callable[[Frame], Any]
"""A compiled expression: evaluates to a value in the given frame."""

StmtFn = Callable[[Frame], 'Signal | None']
"""A compiled statement: returns None normally, or BREAK/CONTINUE/RETURN."""

StoreFn = Callable[[Frame, Any], None]
"""A compiled assignment target: stores a value in the given frame."""

GenFn = Callable[[Frame], Generator[Any, Any, Any]]
"""Compiled code in generator mode: returns a host generator whose return
value is the value (or signal) of the code."""

Token = tuple[str, Any, int]
"""A token: (kind, value, line).  The value of a STRING token is a
(prefix, body) pair; for every other kind it is the token text."""

Args = tuple[Any, ...]
"""Positional arguments of a call."""

Kwargs = dict[str, Any] | None
"""Keyword arguments of a call, or None when there are none."""
