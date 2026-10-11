"""Measure how long one simple statement (`x = x + 1`) takes.

The timed loop runs the statement ten times per iteration; an otherwise
identical empty loop is timed too, and the statement's own cost is the
difference divided by ten.  Unrolling makes the loop overhead a small part
of what is measured, so the subtraction is stable even when the overhead is
large (as it is deep in the interpreter tower).  Both loops are calibrated to
run for a noticeable time and the best of several repetitions is kept.

Prints one JSON line.  Usage: simple_statement.py [seconds]
"""

from __future__ import annotations

import sys
import time

PROGRAM_START: float = time.perf_counter()
"""When this program started running (after the interpreters below it
started up), so that the caller can tell start-up time from run time."""

UNROLL: int = 10


def loop_with_statements(n: int) -> float:
    """The time n iterations of a loop running the statement UNROLL times take."""
    x: int = 0
    t0: float = time.perf_counter()
    for i in range(n):
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
    t1: float = time.perf_counter()
    return t1 - t0


def empty_loop(n: int) -> float:
    """The time n iterations of an empty loop take."""
    t0: float = time.perf_counter()
    for i in range(n):
        pass
    t1: float = time.perf_counter()
    return t1 - t0


def calibrate(budget: float) -> int:
    """The number of iterations that makes one timed loop take about budget/20 seconds."""
    n: int = 1
    while True:
        t: float = loop_with_statements(n)
        if t >= budget / 20 or n >= 1 << 30:
            return n
        n = n * 2


def main() -> None:
    """Calibrate, time both loops a few times and print the best times."""
    budget: float = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    n: int = calibrate(budget)
    best_with: float = float('inf')
    best_empty: float = float('inf')
    for _ in range(5):
        best_with = min(best_with, loop_with_statements(n))
        best_empty = min(best_empty, empty_loop(n))
    with_ns: float = best_with / n * 1e9
    empty_ns: float = best_empty / n * 1e9
    statement_ns: float = (with_ns - empty_ns) / UNROLL
    program_seconds: float = time.perf_counter() - PROGRAM_START
    print(f'{{"n": {n}, "unroll": {UNROLL}, "loop_with_statements_ns": {with_ns:.3f}, '
          f'"empty_loop_ns": {empty_ns:.3f}, "statement_ns": {statement_ns:.3f}, '
          f'"program_seconds": {program_seconds:.3f}}}')


main()
