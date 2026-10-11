"""The import system.

A module is interpreted when its source file can be found: top-level
modules are searched for in SEARCH_PATH (which the command line sets up,
see cli.py) and submodules in their parent package's __path__.  Everything
else, such as the standard library, is imported from the host with
importlib, so interpreted programs use the host's library modules.

Interpreted modules are ordinary host module objects whose __dict__ is the
globals of the module's code.  They are registered in MODULES and, unless
the host has a module of the same name (the interpreter's own modules when
boros runs itself), in sys.modules too, so that host code finds them by
name; module_for() looks in both.  A finder on sys.meta_path (BorosFinder)
makes host-initiated imports (importlib.import_module, importlib.reload)
interpret the program's modules as well.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import os
import sys
import types
from typing import TYPE_CHECKING, Any, cast

from ..lexer import decode_source
from ..parser import parse
from ..syntax import Scope
from .builtin_functions import BUILTINS
from .errors import SOURCES
from .tracebacks import traceback_module

if TYPE_CHECKING:
    from collections.abc import Iterable
    from importlib.abc import Loader

    from ..compiler.compiler import Compiler
    from ..core_types import Frame
    from ..syntax import Module
    from .objects import Signal


MODULES: dict[str, types.ModuleType] = {}
"""The modules loaded (and interpreted) by this interpreter, by name."""

SEARCH_PATH: list[str] = []
"""The directories searched for top-level modules to interpret."""

HOST_PATH: set[str] = set(sys.path)
"""The host's own import path when the interpreter started.  Directories
the program adds to sys.path are searched for modules to interpret too."""

INTERPRETED_STDLIB: dict[str, int] = {'dataclasses': 1}
"""Pure-Python standard library modules that are interpreted from their
source instead of imported from the host, because they must work on
interpreted classes: dataclasses reads and generates class attributes."""

HOST_OVERRIDES: dict[str, list[str]] = {'functools': ['total_ordering']}
"""Host modules that programs get a copy of, in which these names are
replaced by the functions of host_overrides that understand interpreted
classes."""


# -- running module code -------------------------------------------------------

def run_code(tree: Module, filename: str, g: Frame, loc: Frame | None) -> Signal | None:
    """Compile and run a parsed module in globals g; with a separate
    locals mapping, top-level names are bound in loc like a class body."""
    from ..compiler.compiler import Compiler
    if '__builtins__' not in g:
        g['__builtins__'] = BUILTINS
    top: Scope = tree.scope
    comp: Compiler = Compiler(g, filename, top)
    if loc is None or loc is g:
        return comp.module_body(tree.body)(g)
    scope: Scope = Scope('class', '<module>', top)
    scope.assigned = top.assigned
    scope.globals = top.globals
    scope.exec_locals = True
    scope.mapping = type(loc) is not dict
    comp.stack.append(scope)
    return comp.module_body(tree.body)(loc)


def run_source(src: str, filename: str, g: Frame) -> None:
    """Parse and run module source text in globals g, remembering its lines
    for tracebacks."""
    SOURCES[filename] = src.split('\n')
    tree: Module = parse(src, filename)
    run_code(tree, filename, g, None)


def read_source(filename: str) -> str:
    """The text of a source file, decoded as PEP 263 says (see
    lexer.decode_source): UTF-8 unless a coding declaration says otherwise."""
    with open(filename, 'rb') as f:
        return decode_source(f.read())


# -- module objects ------------------------------------------------------------

def module_dict(m: types.ModuleType) -> dict[str, Any]:
    """The namespace of a module (for `from m import *`)."""
    return m.__dict__


def module_for(name: str) -> types.ModuleType:
    """The already imported module with this name, interpreted or host."""
    m: types.ModuleType | None = MODULES.get(name)
    if m is None:
        m = sys.modules[name]
    return m


def new_module(name: str, filename: str) -> types.ModuleType:
    """A new, empty module object for the source file `filename`."""
    m: types.ModuleType = types.ModuleType(name)
    m.__file__ = filename
    return m


# -- finding and loading modules -----------------------------------------------

def find_source(name: str, path: Iterable[str]) -> tuple[str | None, bool]:
    """Search the directories of path for module `name`: returns the source
    file and whether it is a package (a directory with an __init__.py), or
    (None, False) if it is not found."""
    for d in path:
        base: str = os.path.join(d, name)
        init: str = os.path.join(base, '__init__.py')
        if os.path.isfile(init):
            return init, True
        f: str = base + '.py'
        if os.path.isfile(f):
            return f, False
    return None, False


def current_package(g: Frame) -> Any:
    """The package that relative imports in the module with globals g are
    relative to: its __package__, or else the package derived from its
    __name__ (a package is its own parent)."""
    pkg: Any = g.get('__package__')
    if pkg is not None:
        return pkg
    modname: Any = g.get('__name__', '')
    if '__path__' in g:
        return modname
    return modname.rpartition('.')[0]


def resolve_relative(name: str, g: Frame, level: int) -> str:
    """The absolute name for a relative import of `name` with `level` leading
    dots, made by the module with globals g."""
    pkg: Any = current_package(g)
    if not pkg:
        raise ImportError('attempted relative import with no known parent package')
    bits: list[str] = pkg.split('.')
    if level - 1 >= len(bits):
        raise ImportError('attempted relative import beyond top-level package')
    base: str = '.'.join(bits[:len(bits) - (level - 1)])
    if name:
        return base + '.' + name
    return base


def search_path() -> list[str]:
    """The directories searched for top-level modules to interpret: those
    the program added to sys.path (in order), then SEARCH_PATH."""
    out: list[str] = []
    for p in sys.path:
        if p and p not in HOST_PATH and p not in out:
            out.append(p)
    for p in SEARCH_PATH:
        if p not in out:
            out.append(p)
    return out


def register_module(name: str, m: types.ModuleType) -> None:
    """Make interpreted module m sys.modules[name], as CPython does, unless
    the host already has a different module of that name or a different
    parent package: host code (and the interpreter's own lazy imports, when
    boros runs itself) keeps its own modules."""
    pname: str = name.rpartition('.')[0]
    if pname and sys.modules.get(pname) is not MODULES.get(pname):
        return
    if sys.modules.get(name, m) is m:
        sys.modules[name] = m


def unregister_module(name: str, m: types.ModuleType) -> None:
    """Forget module m, whose code failed to run."""
    if MODULES.get(name) is m:
        del MODULES[name]
    if sys.modules.get(name) is m:
        del sys.modules[name]


def load_module(name: str, filename: str, is_pkg: bool) -> types.ModuleType:
    """Create module `name` from the source file `filename`, register it in
    MODULES (and sys.modules) and run its code.  If running it fails, the
    module is unregistered again and the error propagates."""
    loader: BorosLoader = BorosLoader(filename, is_pkg)
    spec: importlib.machinery.ModuleSpec = make_spec(name, loader)
    m: types.ModuleType = loader.create_module(spec)
    m.__spec__ = spec
    m.__loader__ = cast('Loader', loader)
    register_module(name, m)
    try:
        run_source(read_source(filename), filename, m.__dict__)
    except BaseException:
        unregister_module(name, m)
        raise
    return m


class BorosLoader:
    """The importlib loader of a module this interpreter runs, so that
    imports started by host code (importlib.import_module, importlib.reload)
    get the same interpreted modules as the import statement."""

    def __init__(self, filename: str, is_pkg: bool) -> None:
        self.filename: str = filename
        self.is_pkg: bool = is_pkg

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> types.ModuleType:
        """A new module object for spec, registered in MODULES."""
        name: str = spec.name
        m: types.ModuleType = new_module(name, self.filename)
        if self.is_pkg:
            m.__path__ = [os.path.dirname(self.filename)]
            m.__package__ = name
        else:
            m.__package__ = name.rpartition('.')[0]
        MODULES[name] = m
        return m

    def exec_module(self, m: types.ModuleType) -> None:
        """Run (or, for importlib.reload, run again) the module's code."""
        name: str = m.__name__
        MODULES[name] = m
        try:
            run_source(read_source(self.filename), self.filename, m.__dict__)
        except BaseException:
            if MODULES.get(name) is m:
                del MODULES[name]
            raise

    def is_package(self, name: str) -> bool:
        """Whether the module is a package."""
        return self.is_pkg


def make_spec(name: str, loader: BorosLoader) -> importlib.machinery.ModuleSpec:
    """The module spec of interpreted module `name`, loaded by `loader`."""
    spec: importlib.machinery.ModuleSpec = importlib.machinery.ModuleSpec(name, cast('Loader', loader),
                                                                          origin=loader.filename)
    if loader.is_pkg:
        spec.submodule_search_locations = [os.path.dirname(loader.filename)]
    spec.has_location = True
    return spec


class BorosFinder:
    """The sys.meta_path entry that finds the modules this interpreter runs
    when host code imports them: top-level modules on search_path(), and
    submodules of interpreted packages that are in sys.modules."""

    def find_spec(self, name: str, path: Any = None, target: Any = None) -> importlib.machinery.ModuleSpec | None:
        """The spec of module `name`, or None to leave it to the host."""
        pname, _, short = name.rpartition('.')
        dirs: list[str]
        if pname:
            parent: types.ModuleType | None = MODULES.get(pname)
            if parent is None or sys.modules.get(pname) is not parent or not path:
                return None
            dirs = list(path)
        else:
            dirs = search_path()
        filename, is_pkg = find_source(short, dirs)
        if filename is None:
            return None
        return make_spec(name, BorosLoader(filename, is_pkg))


def install_finder() -> None:
    """Let host-initiated imports find the program's modules (see BorosFinder)."""
    sys.meta_path.insert(0, BorosFinder())


def import_submodule(name: str, g: Frame) -> types.ModuleType:
    """Import the dotted module `name`: first its parent package, then the
    submodule from the parent's __path__.  Submodules of host packages are
    imported from the host."""
    pname, _, short = name.rpartition('.')
    parent: types.ModuleType = import_module(pname, g, 0)
    if pname not in MODULES:
        return importlib.import_module(name)
    m: types.ModuleType | None = MODULES.get(name)
    if m is not None:
        # importing the parent package imported this submodule too
        return m
    filename, is_pkg = find_source(short, getattr(parent, '__path__', []))
    if filename is None:
        raise ModuleNotFoundError(f"No module named '{name}'", name=name)
    m = load_module(name, filename, is_pkg)
    setattr(parent, short, m)
    return m


def import_module(name: str, g: Frame, level: int) -> types.ModuleType:
    """Import module `name` and return it, as `import name` does.

    level > 0 is a relative import (that many leading dots) made by the
    module with globals g.  A module found on SEARCH_PATH is interpreted
    (once; later imports return the same module), any other one is
    imported from the host."""
    if level > 0:
        name = resolve_relative(name, g, level)
    m: types.ModuleType | None = MODULES.get(name)
    if m is not None:
        return m
    if '.' in name:
        return import_submodule(name, g)
    filename, is_pkg = find_source(name, search_path())
    if filename is None:
        return host_module(name)
    return load_module(name, filename, is_pkg)


def host_module(name: str) -> types.ModuleType:
    """Import top-level module `name`, which is not on the search path, from
    the host.  Three kinds of module are special: the traceback module is
    replaced by the interpreter's own (see runtime.tracebacks); a module of
    INTERPRETED_STDLIB is interpreted from the standard library's source;
    and a module with HOST_OVERRIDES is a private copy with replacements."""
    if name == 'traceback':
        tb: types.ModuleType = traceback_module()
        MODULES[name] = tb
        return tb
    if name in INTERPRETED_STDLIB:
        interpreted: types.ModuleType | None = interpreted_stdlib_module(name)
        if interpreted is not None:
            return interpreted
    m: types.ModuleType = importlib.import_module(name)
    over: list[str] | None = HOST_OVERRIDES.get(name)
    if over is None:
        return m
    return overridden_module(m, name, over)


def interpreted_stdlib_module(name: str) -> types.ModuleType | None:
    """Interpret standard library module `name` from its source, or None if
    its source cannot be found."""
    filename: str = os.path.join(os.path.dirname(os.__file__), name + '.py')
    if not os.path.isfile(filename):
        return None
    m: types.ModuleType = load_module(name, filename, False)
    # the module finds itself there (sys.modules[__name__])
    sys.modules[name] = m
    return m


def overridden_module(m: types.ModuleType, name: str, over: list[str]) -> types.ModuleType:
    """A private copy of host module m in which the names `over` are replaced
    by the functions of host_overrides that understand interpreted classes."""
    from . import host_overrides
    m2: types.ModuleType = types.ModuleType(name, m.__doc__)
    m2.__dict__.update(m.__dict__)
    for n in over:
        m2.__dict__[n] = getattr(host_overrides, n)
    MODULES[name] = m2
    return m2


def main_module_source(name: str) -> tuple[str, str | None]:
    """Locate the source file that `python -m name` runs, importing parent
    packages first.  Returns (filename, package name); for a package, that
    is its __main__ submodule."""
    path: Iterable[str]
    short: str
    if '.' in name:
        parent_name: str = name.rpartition('.')[0]
        parent: types.ModuleType = import_module(parent_name, {}, 0)
        path = getattr(parent, '__path__', [])
        short = name.rpartition('.')[2]
    else:
        path = SEARCH_PATH
        short = name
    filename, is_pkg = find_source(short, path)
    if filename is None:
        raise ImportError(f"No module named '{name}'")
    if is_pkg:
        import_module(name, {}, 0)
        return main_module_source(name + '.__main__')
    return filename, name.rpartition('.')[0] or None
