"""boros must implement Python itself: it may not hand code to the host's
eval/exec/compile or use the ast/code/codeop/dis/marshal modules."""

from __future__ import annotations

import io
import tokenize
from typing import TYPE_CHECKING

from helpers import PACKAGE, PYTHON, SRC, run

if TYPE_CHECKING:
    from pathlib import Path

FORBIDDEN_NAMES: set[str] = {'eval', 'exec', 'compile', 'breakpoint', '__build_class__'}
FORBIDDEN_MODULES: set[str] = {'ast', 'code', 'codeop', 'dis', 'marshal', 'symtable', 'importlib.util', 'runpy'}


def package_sources() -> list[Path]:
    """Every source file of the boros package."""
    return sorted(PACKAGE.rglob('*.py'))


def test_source_does_not_reference_host_eval() -> None:
    """No source file mentions eval, exec, compile, ... as a plain name."""
    bad: list[tuple[str, int, str]] = []
    for path in package_sources():
        bad.extend(forbidden_names(path))
    assert not bad, f'host eval/exec/compile referenced at {bad}'


def forbidden_names(path: Path) -> list[tuple[str, int, str]]:
    """The (file name, line, name) of each forbidden name used in a source
    file, other than as an attribute name."""
    src: str = path.read_text()
    prev: tokenize.TokenInfo | None = None
    bad: list[tuple[str, int, str]] = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        # `re.compile` (an attribute) is regex compilation, which is fine
        is_attribute: bool = prev is not None and prev.string == '.'
        if tok.type == tokenize.NAME and tok.string in FORBIDDEN_NAMES and not is_attribute:
            bad.append((path.name, tok.start[0], tok.string))
        if tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT):
            prev = tok
    return bad


def test_source_does_not_import_code_tools() -> None:
    """No source file imports a module that compiles or inspects Python code."""
    for path in package_sources():
        for line in path.read_text().splitlines():
            s: str = line.strip()
            for mod in FORBIDDEN_MODULES:
                assert not s.startswith(f'import {mod}'), (path.name, line)
                assert not s.startswith(f'from {mod} import'), (path.name, line)


def test_runs_without_host_eval(tmp_path: Path) -> None:
    """Run the interpreter in a process where the host's eval, exec and
    compile builtins have been deleted and the ast module is blocked."""
    prog: Path = tmp_path / 'prog.py'
    prog.write_text(
        'exec("x = 6 * 7")\n'
        'print(x, eval("x + 1"))\n'
        'code = compile("y = [i * i for i in range(4)]", "<s>", "exec")\n'
        'exec(code)\n'
        'print(y)\n'
        'class A:\n'
        '    def f(self):\n'
        '        return "method"\n'
        'print(A().f())\n')
    guard: Path = tmp_path / 'guard.py'
    guard.write_text(
        'import builtins, sys\n'
        f'sys.path.insert(0, {str(SRC)!r})\n'
        'from boros.cli import start\n'
        'import boros.compiler, boros.parser, boros.runtime  # loaded before the host loses compile()\n'
        'for name in ("eval", "exec", "compile"):\n'
        '    delattr(builtins, name)\n'
        'for mod in ("ast", "code", "codeop", "dis", "marshal", "symtable"):\n'
        '    sys.modules[mod] = None\n'
        'sys.exit(start(["boros"] + sys.argv[1:]))\n')
    code, out, err = run([PYTHON, str(guard), str(prog)], cwd=tmp_path)
    assert code == 0, err
    assert out == '42 43\n[0, 1, 4, 9]\nmethod\n'
