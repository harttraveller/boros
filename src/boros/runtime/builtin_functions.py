"""The builtins seen by interpreted programs.

BUILTINS starts as a copy of the host's builtins module, without the few
names (such as __build_class__) that interpreted programs must not reach.
The builtins that have to understand interpreted objects (Class and
Instance) are then replaced by the b_* functions below: getattr and its
relatives go through the interpreted attribute protocol, dir() and vars()
know about class namespaces and instance dicts, isinstance() and friends
come from typechecks, and compile(), exec(), eval() and __import__() run
code with this interpreter instead of the host's.

The forms of locals(), globals(), vars(), dir(), eval() and exec() that
depend on the calling frame are handled by the compiler when the program
calls them by name (see compiler/calls.py); the functions here cover the
remaining cases.
"""

from __future__ import annotations

import builtins as host_builtins
import types
from typing import TYPE_CHECKING, Any

from ..lexer import decode_source
from ..parser import parse, parse_eval, parse_single
from ..syntax import ExprStmt, Return, Scope
from .attributes import bind_value, delattr_any, getattr_any, setattr_any
from .calls import call
from .errors import SOURCES
from .exceptions import SPECIAL_ATTRS, getattr_special
from .lookup import K_FUNC, NONBINDING, lookup
from .objects import Class, Instance
from .suggestions import GLOBALS_KEY
from .typechecks import b_callable, b_isinstance, b_issubclass, type_name

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..compiler.compiler import Compiler
    from ..core_types import Frame
    from ..syntax import Expression, Module, Statement
    from .lookup import Entry


# -- attributes ----------------------------------------------------------------

def attr_name_error(name: Any) -> TypeError:
    """The error for an attribute name, given to getattr(), setattr() or
    hasattr(), that is not a string."""
    return TypeError(f"attribute name must be string, not '{type_name(name)}'")


def b_getattr(o: Any, name: Any, *default: Any) -> Any:
    """getattr(o, name[, default]) for interpreted and host objects."""
    if type(name) is not str:
        raise attr_name_error(name)
    get: Any = getattr_special if name in SPECIAL_ATTRS else getattr_any
    if default:
        try:
            return get(o, name)
        except AttributeError:
            return default[0]
    return get(o, name)


def b_setattr(o: Any, name: Any, value: Any) -> None:
    """setattr(o, name, value) for interpreted and host objects."""
    if type(name) is not str:
        raise attr_name_error(name)
    setattr_any(o, name, value)


def b_delattr(o: Any, name: Any) -> None:
    """delattr(o, name) for interpreted and host objects."""
    delattr_any(o, name)


def b_hasattr(o: Any, name: Any) -> bool:
    """hasattr(o, name): whether getattr(o, name) succeeds without raising
    AttributeError."""
    if type(name) is not str:
        raise attr_name_error(name)
    try:
        getattr_any(o, name)
    except AttributeError:
        return False
    return True


# -- namespaces ----------------------------------------------------------------

def b_vars(*args: Any) -> Any:
    """vars(x): the attribute dict of an instance, a read-only view of a
    class namespace, or the host vars() of a host object.  (vars() with no
    argument is handled by the compiler; this fallback returns {}.)"""
    if not args:
        return {}
    x: Any = args[0]
    t: type = type(x)
    if t is Instance:
        if x.cls.dictless:
            raise TypeError('vars() argument must have __dict__ attribute')
        return x.d
    if t is Class:
        return types.MappingProxyType(x.ns)
    return vars(x)


def class_dir(c: Class) -> set[str]:
    """The attribute names dir() lists for class c: every name in the
    namespace of each class on its MRO (host classes are asked with the
    host's dir()), and __dict__ and __weakref__ unless instances are
    dictless."""
    names: set[str] = set()
    if not c.dictless:
        names.add('__dict__')
        names.add('__weakref__')
    for k in c.mro:
        if type(k) is Class:
            names.update(k.ns)
        else:
            names.update(dir(k))
    return names


def instance_dir(x: Instance) -> list[Any]:
    """dir(x) for an interpreted instance: the sorted result of its class's
    __dir__ method if it defines one, otherwise the names of the instance's
    own attributes and of its class's attributes."""
    e: Entry = lookup(x.cls, '__dir__')
    if e[0] is K_FUNC:
        listing: Any = call(bind_value(e[1], e[0], x, x.cls), (), None)
        return sorted(listing)
    names: set[str] = class_dir(x.cls)
    names.update(x.d)
    names.add('__class__')
    return sorted(names)


def b_dir(*args: Any) -> Any:
    """dir(x): the sorted attribute names of an interpreted instance or
    class, or the host dir() of a host object.  (dir() with no argument is
    handled by the compiler; this fallback returns [].)"""
    if not args:
        return []
    x: Any = args[0]
    t: type = type(x)
    if t is Instance:
        return instance_dir(x)
    if t is Class:
        return sorted(class_dir(x))
    return dir(x)


def b_locals() -> dict[str, Any]:
    """locals() reached other than by a direct call (which the compiler
    handles with the calling frame): an empty dict."""
    return {}


def b_globals() -> dict[str, Any]:
    """globals() reached other than by a direct call (which the compiler
    handles with the calling frame): an empty dict."""
    return {}


# -- running code --------------------------------------------------------------

class CodeObject:
    """The result of the compile() builtin: a parsed but not yet compiled
    module or expression, which exec() or eval() compile and run."""

    def __init__(self, tree: Module, filename: str, mode: str, source: str) -> None:
        self.tree: Module = tree
        self.co_filename: str = filename
        self.mode: str = mode
        self.source: str = source

    def __repr__(self) -> str:
        return f'<code object <module> at 0x{id(self):x}, file "{self.co_filename}">'


def source_text(source: Any) -> str:
    """Source code given to compile(), exec() or eval(), as a str (bytes are
    decoded as PEP 263 says, see lexer.decode_source)."""
    if type(source) is bytes:
        return decode_source(source)
    return source


def b_compile(source: Any, filename: str, mode: str, flags: int = 0, dont_inherit: bool = False,
              optimize: int = -1) -> CodeObject:
    """compile(source, filename, mode): parse the source for a later exec()
    or eval(), remembering its lines for tracebacks.  The flags,
    dont_inherit and optimize arguments are accepted and ignored."""
    text: str = source_text(source)
    tree: Module
    if mode == 'eval':
        tree = parse_eval(text, filename)
    elif mode == 'exec':
        tree = parse(text, filename)
    elif mode == 'single':
        tree = parse_single(text, filename)
    else:
        raise ValueError("compile() mode must be 'exec', 'eval' or 'single'")
    check_compiles(tree, filename, mode)
    SOURCES[filename] = text.split('\n')
    return CodeObject(tree, filename, mode, text)


def check_compiles(tree: Module, filename: str, mode: str) -> None:
    """Compile a parsed tree and throw the result away, so that compile()
    itself raises the SyntaxErrors the compiler detects (such as 'return'
    outside function), as CPython's does.  (Compiling does not change the
    tree, which exec() or eval() compile again with the real globals.)"""
    from ..compiler.compiler import Compiler
    comp: Compiler = Compiler({}, filename, tree.scope)
    first: Statement | None = tree.body[0] if tree.body else None
    if mode == 'eval' and isinstance(first, ExprStmt):
        comp.expr(first.value)
    else:
        comp.module_body(tree.body)


def b_exec(source: Any, globals: Frame | None = None, locals: Frame | None = None, own_frame: bool = False) -> None:
    """exec(source[, globals[, locals]]): run source text or a code object
    from compile() as a module body in globals (a new dict if omitted),
    binding top-level names in a separate locals mapping if one is given.

    exec(source) without explicit globals is redirected here by the
    compiler with the calling frame (own_frame=True)."""
    from .modules import run_code
    if globals is None:
        globals = {}
    tree: Module
    filename: str
    if type(source) is CodeObject:
        tree = source.tree
        filename = source.co_filename
    else:
        text: str = source_text(source)
        filename = '<string>'
        SOURCES[filename] = text.split('\n')
        tree = parse(text, filename)
    run_code(tree, filename, globals, locals)


def b_eval(source: Any, globals: Frame | None = None, locals: Frame | None = None, own_frame: bool = False) -> Any:
    """eval(source[, globals[, locals]]): the value of an expression, given
    as source text or as a code object from compile(..., 'eval'), in globals
    (a new dict if omitted) and an optional separate locals mapping.  A code
    object compiled for 'exec' is run like exec() and gives None.

    eval(source) without explicit globals is redirected here by the
    compiler with the calling frame (own_frame=True)."""
    from .modules import run_code
    if globals is None:
        globals = {}
    tree: Module
    filename: str
    if type(source) is CodeObject:
        tree = source.tree
        filename = source.co_filename
        if source.mode != 'eval':
            run_code(tree, filename, globals, locals)
            return None
    else:
        filename = '<string>'
        tree = parse_eval(source_text(source), filename)
    return evaluate(tree, filename, globals, locals)


def eval_expression(tree: Module) -> Expression:
    """The expression of a tree parsed in 'eval' mode, whose only statement
    holds it.  That statement is replaced by `return <expression>`; both
    statement kinds keep the expression in `.value`, so a code object from
    compile(..., 'eval') can be evaluated any number of times."""
    stmt: Statement = tree.body[0]
    if not isinstance(stmt, (ExprStmt, Return)) or stmt.value is None:
        raise SystemError('eval() of a tree without an expression')
    expr: Expression = stmt.value
    tree.body[0] = Return(1, expr)
    return expr


def evaluate(tree: Module, filename: str, g: Frame, loc: Frame | None) -> Any:
    """Compile and evaluate the expression of a tree parsed in 'eval' mode,
    with globals g.  A separate locals mapping loc is searched first, as in
    a class body."""
    from ..compiler.compiler import Compiler
    expr: Expression = eval_expression(tree)
    if '__builtins__' not in g:
        g['__builtins__'] = BUILTINS
    top: Scope = tree.scope
    comp: Compiler = Compiler(g, filename, top)
    fr: Frame = g
    if loc is not None and loc is not g:
        scope: Scope = Scope('class', '<module>', top)
        scope.assigned = top.assigned
        scope.exec_locals = True
        scope.mapping = type(loc) is not dict
        comp.stack.append(scope)
        fr = loc
    return comp.expr(expr)(fr)


def b_import(name: str, globals: Frame | None = None, locals: Frame | None = None, fromlist: Sequence[str] = (),
             level: int = 0) -> types.ModuleType:
    """__import__(name, globals, locals, fromlist, level): import a module as
    an import statement would.  Returns the module itself when fromlist is
    non-empty, otherwise the top-level package of a dotted name."""
    from .modules import import_module, module_for
    g: Frame = globals if globals is not None else {}
    m: types.ModuleType = import_module(name, g, level)
    if fromlist:
        return m
    if level == 0 and '.' in name:
        return module_for(name.split('.')[0])
    return m


# -- arithmetic ----------------------------------------------------------------

def b_pow(base: Any, exp: Any, mod: Any = None) -> Any:
    """pow(base, exp[, mod]).  The host's three-argument pow() never reaches
    the interpreted class of an exponent or modulus when the base is a host
    value (Python 3.13 has no reflected form for it): see pow3_instance."""
    if mod is None:
        return pow(base, exp)
    if type(exp) is Instance or type(mod) is Instance:
        return pow3_instance(base, exp, mod)
    return pow(base, exp, mod)


def pow3_instance(base: Any, exp: Any, mod: Any) -> Any:
    """pow(base, exp, mod) with an interpreted exponent or modulus.  Unless
    the base is interpreted too (its __pow__ decides), an instance of a
    subclass of a host type (an int subclass) takes part as its native
    value, and anything else is an error naming the interpreted classes
    (the host would name them all 'Instance')."""
    tb: type = type(base)
    if tb is Instance:
        return pow(base, exp, mod)
    e: Any = exp.native if type(exp) is Instance and exp.native is not None else exp
    m: Any = mod.native if type(mod) is Instance and mod.native is not None else mod
    if type(e) is Instance or type(m) is Instance:
        raise TypeError("unsupported operand type(s) for ** or pow(): "
                        f"'{type_name(base)}', '{type_name(exp)}', '{type_name(mod)}'")
    return pow(base, e, m)


# -- the builtins namespace ----------------------------------------------------

HIDDEN_BUILTINS: dict[str, int] = {'__build_class__': 1, '__loader__': 1, '__spec__': 1, '__builtins__': 1}
"""Host builtins that interpreted programs do not see."""

BUILTINS: dict[str, Any] = {name: getattr(host_builtins, name) for name in dir(host_builtins)
                            if name not in HIDDEN_BUILTINS}
"""The builtins namespace of interpreted programs: the `__builtins__` of
every module the interpreter runs."""

BUILTINS.update({
    'isinstance': b_isinstance,
    'issubclass': b_issubclass,
    'callable': b_callable,
    'getattr': b_getattr,
    'setattr': b_setattr,
    'delattr': b_delattr,
    'hasattr': b_hasattr,
    'vars': b_vars,
    'dir': b_dir,
    'locals': b_locals,
    'globals': b_globals,
    'eval': b_eval,
    'exec': b_exec,
    'compile': b_compile,
    '__import__': b_import,
    'pow': b_pow,
    '__name__': 'builtins',
})


HOST_BUILTINS: dict[str, Any] = host_builtins.__dict__
"""The namespace of the host's builtins module, which programs can add
names to (`builtins.name = value`)."""


def builtins_of(g: Frame) -> dict[str, Any]:
    """The builtins namespace of code running in globals g: BUILTINS, unless
    g['__builtins__'] is some other dict or module, as when exec() is given
    globals with restricted builtins."""
    gb: Any = g.get('__builtins__')
    if gb is None or gb is BUILTINS or gb is host_builtins or gb is HOST_BUILTINS:
        return BUILTINS
    if type(gb) is dict:
        return gb
    return getattr(gb, '__dict__', BUILTINS)


def global_fallback(name: str, g: Frame, b: dict[str, Any]) -> Any:
    """Read a global name found neither in the module globals g nor in its
    builtins b: a name a program added to the builtins module, or else a
    NameError (which keeps g, to suggest a similar name when it is printed)."""
    if b is BUILTINS and name not in HIDDEN_BUILTINS and name in HOST_BUILTINS:
        return HOST_BUILTINS[name]
    e: NameError = NameError(f"name '{name}' is not defined", name=name)
    setattr(e, GLOBALS_KEY, g)
    raise e


def register_nonbinding_builtins() -> None:
    """Record the builtins that the interpreter replaces with functions of
    its own (isinstance, getattr, ...) in NONBINDING, so that they stay
    plain values when stored as class attributes, like host builtins."""
    host: dict[str, Any] = host_builtins.__dict__
    for name, v in BUILTINS.items():
        if v is not host.get(name):
            NONBINDING[id(v)] = 1


register_nonbinding_builtins()


def name_replacements() -> None:
    """Give the functions that replace host builtins in BUILTINS the names
    of the builtins they stand for, so that `exec.__name__` is 'exec'
    rather than 'b_exec' (also in error messages that name the function)."""
    for name, f in BUILTINS.items():
        if f is not getattr(host_builtins, name, f) and callable(f):
            f.__name__ = name
            f.__qualname__ = name


name_replacements()
