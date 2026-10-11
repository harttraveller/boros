"""Render bench/results/tower.html from levels.json and the page template."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE: Path = Path(__file__).resolve().parent
RESULTS: Path = HERE / 'results'


def main() -> None:
    """Embed the measured levels in the template and write the page."""
    data: dict[str, Any] = json.loads((RESULTS / 'levels.json').read_text())
    rows: list[dict[str, Any]] = [
        {'level': r['level'], 'statement_ns': r['statement_ns'], 'startup_seconds': r['startup_seconds']}
        for r in (data[k] for k in sorted(data, key=int))
    ]
    template: str = (RESULTS / 'tower_template.html').read_text()
    page: str = template.replace('/*DATA*/[]', json.dumps(rows))
    (RESULTS / 'tower.html').write_text(page)
    print(f"wrote {RESULTS / 'tower.html'}")


if __name__ == '__main__':
    main()
