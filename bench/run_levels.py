"""Measure the cost of a simple statement at each level of the boros tower.

    python bench/run_levels.py MAX_LEVEL [--budget SECONDS] [--repeat N]

Level 0 is CPython; level N runs bench/simple_statement.py under N nested
copies of boros.  For every level this records the time per statement (from
the benchmark's own timer, so start-up is excluded) and the start-up time
(the wall time of the run minus the time the benchmark program itself ran).
Results are merged into bench/results/levels.json as they arrive, so a long
run can be resumed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from tower import run_tower

HERE: Path = Path(__file__).resolve().parent
RESULTS: Path = HERE / 'results' / 'levels.json'
BENCH: str = str(HERE / 'simple_statement.py')


def load_results() -> dict[str, Any]:
    """Previously recorded results, keyed by level."""
    if RESULTS.exists():
        data: dict[str, Any] = json.loads(RESULTS.read_text())
        return data
    return {}


def save_results(results: dict[str, Any]) -> None:
    """Write the results file."""
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')


def measure_statement(level: int, budget: float) -> dict[str, Any]:
    """Run the statement benchmark under `level` interpreters."""
    t0: float = time.perf_counter()
    proc = run_tower(level, BENCH, [str(budget)])
    elapsed: float = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(f'level {level} benchmark failed:\n{proc.stderr}')
    result: dict[str, Any] = json.loads(proc.stdout.strip().splitlines()[-1])
    result['wall_seconds'] = elapsed
    result['startup_seconds'] = elapsed - result['program_seconds']
    return result


def measure_level(level: int, budget: float, repeat: int) -> dict[str, Any]:
    """Best-of-`repeat` measurements for one level."""
    best: dict[str, Any] | None = None
    startups: list[float] = []
    for _ in range(repeat):
        run: dict[str, Any] = measure_statement(level, budget)
        startups.append(run['startup_seconds'])
        if best is None or run['statement_ns'] < best['statement_ns']:
            best = run
    assert best is not None
    best['startup_seconds'] = min(startups)
    best['level'] = level
    best['repeat'] = repeat
    return best


def main() -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('max_level', type=int)
    parser.add_argument('--min-level', type=int, default=0)
    parser.add_argument('--budget', type=float, default=2.0, help='seconds per timed loop (approximately)')
    parser.add_argument('--repeat', type=int, default=3)
    parser.add_argument('--deep-repeat', type=int, default=1, help='repeats for levels >= 4')
    opts = parser.parse_args()
    results: dict[str, Any] = load_results()
    for level in range(opts.min_level, opts.max_level + 1):
        repeat: int = opts.repeat if level < 4 else opts.deep_repeat
        print(f'level {level} ...', flush=True)
        result: dict[str, Any] = measure_level(level, opts.budget, repeat)
        results[str(level)] = result
        save_results(results)
        print(f"  statement {result['statement_ns']:.1f} ns, loop {result['loop_with_statements_ns']:.1f} ns, "
              f"start-up {result['startup_seconds']:.2f} s", flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
