"""Run a program under a tower of nested boros interpreters.

    python bench/tower.py LEVEL program.py [args...]

Level 0 runs the program on CPython directly, level 1 under boros, level 2
under boros running boros, and so on.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SRC: Path = Path(__file__).resolve().parent.parent / 'src'


def tower_command(level: int, program: str, args: list[str]) -> list[str]:
    """The command line that runs `program` under `level` interpreters."""
    return [sys.executable] + ['-m', 'boros'] * level + [program, *args]


def run_tower(level: int, program: str, args: list[str],
              timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    """Run `program` under `level` interpreters, capturing its output."""
    env: dict[str, str] = dict(os.environ, PYTHONPATH=str(SRC))
    return subprocess.run(tower_command(level, program, args), env=env, capture_output=True, text=True,
                          timeout=timeout, check=False)


def main() -> int:
    """Command-line entry point."""
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    level: int = int(sys.argv[1])
    env: dict[str, str] = dict(os.environ, PYTHONPATH=str(SRC))
    return subprocess.call(tower_command(level, sys.argv[2], sys.argv[3:]), env=env)


if __name__ == '__main__':
    sys.exit(main())
