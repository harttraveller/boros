"""Plot bench/results/levels.json as bench/results/levels.png.

Left: time per simple statement at each level of the tower (log scale), with
the slowdown factor from one level to the next.  Right: that slowdown factor
on its own (linear scale), roughly ×10 to ×16 per level from level 2 on.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullLocator

HERE: Path = Path(__file__).resolve().parent
RESULTS: Path = HERE / 'results' / 'levels.json'
OUTPUT: Path = HERE / 'results' / 'levels.png'

SURFACE: str = '#fcfcfb'
TEXT_PRIMARY: str = '#0b0b0b'
TEXT_SECONDARY: str = '#52514e'
GRID: str = '#e4e3df'
SERIES: str = '#2a78d6'
SERIES_2: str = '#eb6834'


def human_time(ns: float) -> str:
    """Format a duration given in nanoseconds with a sensible unit."""
    for unit, scale in (('s', 1e9), ('ms', 1e6), ('µs', 1e3)):
        if ns >= scale:
            value: float = ns / scale
            return f'{value:.3g} {unit}'
    return f'{ns:.3g} ns'


def load() -> list[dict[str, Any]]:
    """The recorded levels, in order."""
    data: dict[str, Any] = json.loads(RESULTS.read_text())
    return [data[k] for k in sorted(data, key=int)]


def style_axes(ax: Any) -> None:
    """Recessive axes: no box, light horizontal grid, secondary-ink labels."""
    ax.set_facecolor(SURFACE)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(TEXT_SECONDARY)
    ax.tick_params(colors=TEXT_SECONDARY, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def plot_statement_times(ax: Any, levels: list[dict[str, Any]]) -> None:
    """Bars of the time per statement, labelled, with step factors between them."""
    xs: list[int] = [r['level'] for r in levels]
    ys: list[float] = [r['statement_ns'] for r in levels]
    ax.bar(xs, ys, width=0.62, color=SERIES, edgecolor=SURFACE, linewidth=2)
    ax.set_yscale('log')
    for x, y in zip(xs, ys):
        ax.annotate(human_time(y), (x, y), textcoords='offset points', xytext=(0, 5), ha='center',
                    color=TEXT_PRIMARY, fontsize=10, fontweight='bold')
    for i in range(1, len(xs)):
        factor: float = ys[i] / ys[i - 1]
        mid_y: float = (ys[i] * ys[i - 1]) ** 0.5
        ax.annotate(f'×{factor:.0f}', ((xs[i] + xs[i - 1]) / 2, mid_y), ha='center', va='center',
                    color=TEXT_SECONDARY, fontsize=9)
    ax.set_xticks(xs, [f'L{x}' for x in xs])
    ax.set_ylim(min(ys) / 3, max(ys) * 6)
    ax.set_ylabel('time per statement (log scale)', color=TEXT_SECONDARY)
    ax.set_title('Time to execute `x = x + 1`', color=TEXT_PRIMARY, loc='left', fontsize=12)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _pos: human_time(v)))
    ax.yaxis.set_minor_locator(NullLocator())


def plot_factors(ax: Any, levels: list[dict[str, Any]]) -> None:
    """The slowdown from each level to the next."""
    xs: list[int] = [r['level'] for r in levels[1:]]
    factors: list[float] = [levels[i]['statement_ns'] / levels[i - 1]['statement_ns'] for i in range(1, len(levels))]
    ax.bar(xs, factors, width=0.62, color=SERIES_2, edgecolor=SURFACE, linewidth=2)
    for x, f in zip(xs, factors):
        ax.annotate(f'×{f:.1f}', (x, f), textcoords='offset points', xytext=(0, 5), ha='center',
                    color=TEXT_PRIMARY, fontsize=10, fontweight='bold')
    ax.set_xticks(xs, [f'L{x - 1}→L{x}' for x in xs])
    ax.set_ylim(0, max(factors) * 1.18)
    ax.set_ylabel('slowdown factor', color=TEXT_SECONDARY)
    ax.set_title('Slowdown added by each level', color=TEXT_PRIMARY, loc='left', fontsize=12)


def main() -> None:
    """Draw both panels and save the PNG."""
    levels: list[dict[str, Any]] = load()
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={'width_ratios': [3, 2]})
    fig.patch.set_facecolor(SURFACE)
    for ax in (left, right):
        style_axes(ax)
    plot_statement_times(left, levels)
    plot_factors(right, levels)
    fig.text(0.01, 0.01, 'L0 = CPython 3.13; Ln = boros running boros ... (n levels) running the benchmark. '
             'Loop overhead is measured separately and subtracted.', color=TEXT_SECONDARY, fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUTPUT, dpi=160, facecolor=SURFACE)
    print(f'wrote {OUTPUT}')


if __name__ == '__main__':
    main()
