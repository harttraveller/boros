"""Name resolution: deciding whether a name is local, global, free or class-level.

The parser records, for every function, class and module, which names are
assigned, declared `global`/`nonlocal`, deleted or bound as parameters (see
`syntax.Scope`).  `Compiler.resolve` combines those facts with the stack of
enclosing scopes and answers with one of the kinds below, plus a detail:

- LOCAL: the name lives in the current frame dict.
- GLOBAL: the name lives in the module's globals (falling back to builtins).
- FREE: the name lives in an enclosing function's frame; the detail is the
  number of `'.up'` links to follow from the current frame to reach it.
- CLASSNS: we are in a class body (and the name is not declared global or
  nonlocal there): it is stored in the class namespace and loaded from it
  first; the detail is how the name resolves *outside* the class, which is
  the fallback when the namespace does not contain it.
- MAPPED: in a comprehension inlined into exec()/eval() code that has a
  separate locals mapping, a name not bound in the comprehension is looked
  up in that mapping (then globally); the detail is the number of '.up'
  links from the comprehension's frame to the mapping.

The kinds are unique `Signal` objects compared with `is`, which is the
fastest comparison available both on the host and inside boros.
"""

from __future__ import annotations

from typing import Any

from ..runtime.objects import Signal
from ..syntax import Scope

LOCAL: Signal = Signal('local')
"""The name is a local variable of the current function (or comprehension)."""

GLOBAL: Signal = Signal('global')
"""The name is a module global (or a builtin)."""

FREE: Signal = Signal('free')
"""The name is a local variable of an enclosing function."""

CLASSNS: Signal = Signal('class namespace')
"""The name is looked up in the class namespace first, then outside it."""

MAPPED: Signal = Signal('exec locals')
"""The name is looked up in the locals mapping of exec() code, then globally."""

LOCAL_RES: tuple[Signal, Any] = (LOCAL, 0)
"""The (shared) resolution result for a local name."""

GLOBAL_RES: tuple[Signal, Any] = (GLOBAL, 0)
"""The (shared) resolution result for a global name."""


def comprehension_scope(assigned: set[str], name: str) -> Scope:
    """The scope of a comprehension: like a function scope whose local
    names are exactly the comprehension's loop targets."""
    scope: Scope = Scope('comp', name, None)
    scope.assigned = assigned
    return scope
