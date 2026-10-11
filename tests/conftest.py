"""pytest configuration: makes the boros sources and the test helpers
importable and registers the markers used by the tests."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))


def pytest_configure(config: pytest.Config) -> None:
    """Register the selfhost and slow markers."""
    config.addinivalue_line('markers', 'selfhost: runs programs under boros running itself (slow)')
    config.addinivalue_line('markers', 'slow: very slow tests (three or more interpreter levels)')
