"""Differential tests: every program in tests/cases must behave the same
under CPython and under boros (stdout, exit code, final error line).

Cases listed in known_failures.py are strict expected failures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from helpers import assert_same, case_files, run_boros, run_host
from known_failures import LEVEL1, LEVEL2

CASES: list[Path] = case_files()


def cases_for(known: dict[str, str]) -> list[Any]:
    """The cases as pytest parameters, the known failures marked as strict
    expected failures with their reason."""
    params: list[Any] = []
    for case in CASES:
        reason: str | None = known.get(case.stem)
        marks: list[Any] = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
        params.append(pytest.param(case, id=case.stem, marks=marks))
    return params


@pytest.mark.parametrize('case', cases_for(LEVEL1))
def test_level1(case: Path) -> None:
    """boros running the case."""
    assert_same(run_host(case), run_boros(case, level=1), case.name)


@pytest.mark.selfhost
@pytest.mark.parametrize('case', cases_for(LEVEL2))
def test_level2(case: Path) -> None:
    """boros running boros running the case."""
    assert_same(run_host(case), run_boros(case, level=2), case.name)
