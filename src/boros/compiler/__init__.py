"""The compiler: turns a syntax tree into a tree of Python closures.

Instead of generating bytecode, boros compiles every expression into a
Python function `f(fr)` that evaluates it in a frame `fr` (a dict of local
variables), and every statement into a function that executes it and
returns None or a control-flow signal (BREAK, CONTINUE, RETURN).  Compound
nodes become closures that call the closures of their children, so running
a program is just calling the closure of its module body.

The `Compiler` class (compiler.py) holds the per-module state and dispatches
each node type to a `compile_*` function in one of the sibling modules:

- scopes.py, names.py: resolving and loading/storing/deleting variables
- operators.py: arithmetic, boolean operators and comparisons
- targets.py: assignment and deletion targets (including unpacking)
- expressions.py, calls.py, comprehensions.py: the other expressions
- statements.py: statements and blocks
- definitions.py: def, lambda and class
- patterns.py: the match statement
- generators.py: the generator-mode compiler for code that can `yield`
"""

from __future__ import annotations

from .compiler import Compiler

__all__ = ['Compiler']
