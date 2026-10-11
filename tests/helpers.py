"""Helpers for running programs under CPython and under boros."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT: Path = Path(__file__).resolve().parent.parent
SRC: Path = ROOT / 'src'
PACKAGE: Path = SRC / 'boros'
# BOROS_INTERP may name a single-file interpreter to test instead of the package.
SINGLE_FILE: str | None = os.environ.get('BOROS_INTERP')
CASES_DIR: Path = ROOT / 'tests' / 'cases'
PYTHON: str = sys.executable


def run(cmd: list[str], cwd: str | Path, timeout: float | None = 120, stdin: str = '') -> tuple[int, str, str]:
    """Run a command with the boros sources importable and deterministic
    hashing, feeding it stdin; returns (exit code, stdout, stderr)."""
    env: dict[str, str] = dict(os.environ, PYTHONHASHSEED='0', PYTHONIOENCODING='utf-8', PYTHONPATH=str(SRC))
    p: subprocess.CompletedProcess[str] = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True,
                                                         timeout=timeout, env=env, check=False)
    return p.returncode, p.stdout, p.stderr


def boros_command(level: int) -> list[str]:
    """The command prefix running `level` nested copies of the interpreter."""
    if SINGLE_FILE:
        return [PYTHON, *[SINGLE_FILE] * level]
    return [PYTHON, '-m', 'boros', *['-m', 'boros'] * (level - 1)]


def run_host(path: str | Path, args: Sequence[str] = (), timeout: float = 120) -> tuple[int, str, str]:
    """Run `path` directly under CPython."""
    path = Path(path)
    return run([PYTHON, str(path), *args], cwd=path.parent, timeout=timeout)


def run_boros(path: str | Path, level: int = 1, args: Sequence[str] = (),
              timeout: float | None = None) -> tuple[int, str, str]:
    """Run `path` under `level` nested copies of the interpreter."""
    path = Path(path)
    cmd: list[str] = [*boros_command(level), str(path), *args]
    if timeout is None:
        timeout = 60 * level
    return run(cmd, cwd=path.parent, timeout=timeout)


def last_line(text: str) -> str:
    """The last non-blank line of text ('' if there is none)."""
    lines: list[str] = [ln for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else ''


def assert_same(host: tuple[int, str, str], boros: tuple[int, str, str], label: str = '') -> None:
    """Assert that boros behaved like CPython: the same stdout and exit
    code, and on failure the same final error line."""
    hcode, hout, herr = host
    bcode, bout, berr = boros
    assert bout == hout, f'{label}: stdout differs\n--- boros stderr ---\n{berr[-3000:]}'
    assert bcode == hcode, f'{label}: exit code {bcode} != {hcode}\n--- boros stderr ---\n{berr[-3000:]}'
    if hcode != 0:
        assert last_line(berr) == last_line(herr), f'{label}: final error line differs'


def case_files() -> list[Path]:
    """Every tests/cases/*.py whose name does not start with an underscore
    (underscore files are helper modules imported by cases)."""
    return sorted(p for p in CASES_DIR.glob('*.py') if not p.name.startswith('_'))
