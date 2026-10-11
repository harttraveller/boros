"""boros: a metacircular Python interpreter, written in Python.

boros tokenizes, parses and compiles Python source code into a tree of
Python closures and then runs them.  It never hands source code to the
host's eval/exec/compile and does not use the ast module.  The interpreter
is written in the subset of Python that it implements, so it can run
itself, which can run itself, and so on:

    python -m boros program.py
    python -m boros -m boros program.py
    python -m boros -m boros -m boros program.py
"""

from __future__ import annotations

__version__: str = '0.1.0'
