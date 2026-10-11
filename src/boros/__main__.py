"""`python -m boros`: run a Python program with the boros interpreter."""

from __future__ import annotations

import sys

from .cli import start

sys.exit(start(sys.argv))
