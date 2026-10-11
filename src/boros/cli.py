"""Command-line entry point: `python -m boros [-c command | -m module | file] [arg ...]`.

Like CPython, the interpreter runs one main program as module __main__:
the source of a script file, a `-c` command string, or the module named
by `-m`.  Before running it, sys.argv and the module search path are set
up the way CPython would; afterwards an uncaught exception is printed as
an interpreted traceback and turned into the exit status.  The whole run
happens on a thread with a very large stack, because every level of
interpreted calls costs several levels of host calls.
"""

from __future__ import annotations

import builtins
import contextlib
import os
import sys
import threading
from typing import TYPE_CHECKING, Any

from .runtime.exceptions import print_exception
from .runtime.modules import (
    MODULES,
    SEARCH_PATH,
    install_finder,
    main_module_source,
    new_module,
    read_source,
    run_source,
)
from .runtime.typechecks import type_name

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType, TracebackType
    from typing import Self

    from .core_types import Frame

USAGE: str = 'usage: python -m boros [-c command | -m module | file] [arg ...]'

PACKAGE_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""The directory containing the boros package, so that `-m boros` (boros
running itself) finds the interpreter's own source."""

RECURSION_LIMIT: int = 1000000
"""The host recursion limit while interpreting; the real limit is the stack."""

STACK_SIZE: int = 512 * 1024 * 1024
"""The stack size, in bytes, of the thread that runs the interpreter."""


# -- choosing the main program -------------------------------------------------

class MainProgram:
    """The program named on the command line: its source text, the file
    name that tracebacks show, and its package (for `-m package.module`)."""

    def __init__(self, src: str, filename: str, package: str | None) -> None:
        self.src: str = src
        self.filename: str = filename
        self.package: str | None = package


def set_path0(directory: str) -> None:
    """Make sys.path[0] the main program's directory, as CPython does (the
    current directory for -m, '' for -c).  If sys.path[0] is the directory
    the host found boros in, it is kept, since the host may still import
    parts of the interpreter lazily."""
    if sys.path and sys.path[0] != PACKAGE_ROOT:
        sys.path[0] = directory
    else:
        sys.path.insert(0, directory)


def module_program(name: str, rest: list[str]) -> MainProgram | int:
    """`-m name`: the source of module `name` (a package runs its
    __main__), found on a search path of the current directory and the
    directory containing boros.  Exit status 1 if there is no such module."""
    SEARCH_PATH.append(os.getcwd())
    SEARCH_PATH.append(PACKAGE_ROOT)
    set_path0(os.getcwd())
    try:
        filename, package = main_module_source(name)
    except ImportError as e:
        sys.stderr.write(f'No module named {name} ({e})\n')
        return 1
    src: str = read_source(filename)
    sys.argv = [filename, *rest]
    return MainProgram(src, filename, package)


def command_program(command: str, rest: list[str]) -> MainProgram:
    """`-c command`: the command string, run as file '<string>'."""
    sys.argv = ['-c', *rest]
    SEARCH_PATH.append(os.getcwd())
    SEARCH_PATH.append(PACKAGE_ROOT)
    set_path0('')
    return MainProgram(command, '<string>', None)


def file_program(filename: str, rest: list[str]) -> MainProgram | int:
    """A script file, whose directory is searched for modules first.  Exit
    status 2 if it cannot be read."""
    try:
        src: str = read_source(filename)
    except OSError as e:
        sys.stderr.write(f"can't open file '{filename}': {e}\n")
        return 2
    sys.argv = [filename, *rest]
    script_dir: str = os.path.dirname(os.path.abspath(filename))
    SEARCH_PATH.append(script_dir)
    SEARCH_PATH.append(PACKAGE_ROOT)
    set_path0(script_dir)
    return MainProgram(src, filename, None)


def find_program(args: list[str]) -> MainProgram | int:
    """The main program for the command-line arguments (without the
    interpreter's own name), with sys.argv and the module search path set
    up for it; an exit status instead if the arguments are wrong."""
    option: str = args[0]
    if option != '-m' and option != '-c':
        return file_program(option, args[1:])
    if len(args) < 2:
        sys.stderr.write(f'Argument expected for the {option} option\n')
        return 2
    if option == '-m':
        return module_program(args[1], args[2:])
    return command_program(args[1], args[2:])


# -- running it ----------------------------------------------------------------

def flush_stdout() -> None:
    """Flush the program's output, ignoring errors (stdout may be closed)."""
    with contextlib.suppress(BaseException):
        sys.stdout.flush()


def exit_status(code: Any) -> int:
    """The process exit status for SystemExit(code): None means 0 and an
    int (including a bool) is used as it is; anything else is printed to
    stderr and means 1."""
    if code is None:
        return 0
    if isinstance(code, int):
        return int(code)
    sys.stderr.write(f'{code}\n')
    return 1


class MainOutcome:
    """The exit status of the main program, as a context manager wrapped
    around running it.  Like CPython's top level, it turns SystemExit into
    the exit status, and prints the interpreted traceback of any other
    exception that escapes the program, which gives exit status 1."""

    def __init__(self) -> None:
        self.status: int = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, typ: type[BaseException] | None, e: BaseException | None, tb: TracebackType | None) -> bool:
        if e is None:
            return False
        if isinstance(e, SystemExit):
            self.status = exit_status(e.code)
        else:
            flush_stdout()
            print_exception(e)
            self.status = 1
        return True


def run_main(src: str, filename: str, g: Frame) -> int:
    """Run the main program's source in globals g; returns the exit status."""
    outcome: MainOutcome = MainOutcome()
    with outcome:
        run_source(src, filename, g)
    return outcome.status


def main(argv: list[str]) -> int:
    """Run the interpreter with command line argv (argv[0] is the
    interpreter's name) and return the exit status."""
    args: list[str] = argv[1:]
    if not args:
        sys.stderr.write(USAGE + '\n')
        return 2
    program: MainProgram | int = find_program(args)
    if isinstance(program, int):
        return program
    m: ModuleType = new_module('__main__', program.filename)
    m.__package__ = program.package
    # as in CPython, the main module's __builtins__ is the builtins module
    m.__dict__['__builtins__'] = builtins
    MODULES['__main__'] = m
    # the program, not the interpreter, is __main__ (at every level of a tower)
    sys.modules['__main__'] = m
    install_finder()
    return run_main(program.src, program.filename, m.__dict__)


# Every interpreted call costs several host frames, so the recursion limit a
# program sets is virtual: sys.getrecursionlimit() reports it, while the host
# limit is kept at least RECURSION_FACTOR times larger (and never lowered).

HOST_SETRECURSIONLIMIT: Callable[[int], None] = sys.setrecursionlimit
"""The host's sys.setrecursionlimit (that of the level below, in a tower)."""

HOST_GETRECURSIONLIMIT: Callable[[], int] = sys.getrecursionlimit
"""The host's sys.getrecursionlimit (that of the level below, in a tower)."""

RECURSION_FACTOR: int = 64
"""Host frames allowed per interpreted frame of the program's recursion limit."""

HOST_RECURSION_CAP: int = 1 << 28
"""The largest host limit requested: each level of a tower multiplies the
request, which must stay a C int."""

VIRTUAL_RECURSION_LIMIT: list[int] = [HOST_GETRECURSIONLIMIT()]
"""The recursion limit the program sees."""


def b_setrecursionlimit(limit: Any) -> None:
    """sys.setrecursionlimit for interpreted programs: set the virtual limit,
    raising the host limit (never lowering it) to match."""
    if type(limit) is not int:
        raise TypeError(f"'{type_name(limit)}' object cannot be interpreted as an integer")
    if limit < 1:
        raise ValueError('recursion limit must be greater or equal than 1')
    VIRTUAL_RECURSION_LIMIT[0] = limit
    want: int = min(limit * RECURSION_FACTOR, HOST_RECURSION_CAP)
    if want > HOST_GETRECURSIONLIMIT():
        HOST_SETRECURSIONLIMIT(want)


def b_getrecursionlimit() -> int:
    """sys.getrecursionlimit for interpreted programs: the virtual limit."""
    return VIRTUAL_RECURSION_LIMIT[0]


def start(argv: list[str]) -> int:
    """Run main() in a thread with a large stack, so that deeply nested
    interpretation does not overflow the C stack."""
    if HOST_GETRECURSIONLIMIT() < RECURSION_LIMIT:
        HOST_SETRECURSIONLIMIT(RECURSION_LIMIT)
    sys.setrecursionlimit = b_setrecursionlimit
    sys.getrecursionlimit = b_getrecursionlimit
    threading.stack_size(STACK_SIZE)
    result: list[int] = [1]

    def target() -> None:
        """The thread's body: run the interpreter, keeping its exit status."""
        result[0] = main(argv)

    t: threading.Thread = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join()
    flush_stdout()
    return result[0]


def run() -> None:
    """Console-script entry point (`boros program.py`)."""
    sys.exit(start(sys.argv))
