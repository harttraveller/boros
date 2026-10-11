"""Calling things: argument binding, interpreted function invocation, instantiation.

Every call made by an interpreted program ends up in `call(f, args, kw)`,
which dispatches on the type of the callee:

* an interpreted `Function` is run by `invoke`, which builds a fresh frame
  (a dict from local variable names to values) and runs the compiled body
  on it;
* a bound `Method` puts its `self` in front of the arguments and calls the
  function it wraps;
* an interpreted `Class` is instantiated by `instantiate` (`__new__`, then
  `__init__`);
* an `Instance` is called through its class's `__call__`;
* anything else is a host callable (a builtin, a host class, a host
  function) and is simply called.

A frame holds the function's parameters and locals under their own names,
plus two bookkeeping entries: '.up' is the frame of the enclosing function
(the closure, used to read free variables) and '.cls' is the class cell
used by zero-argument `super()` and `__class__`.

Positional arguments are a tuple and keyword arguments a dict, or None
when there are none (so the common case needs no dict at all).
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any

from .coroutines import AwaitBody, async_generator, coroutine
from .errors import EXC_REPR, INST_KEY, annotate, annotate_call, exc_repr
from .lookup import K_EMU, K_FUNC, K_MISSING, K_NATIVE, K_NODICT, K_STATIC, lookup
from .objects import MISSING, Class, Function, Instance, Method, Super
from .suggestions import keyword_suggestion
from .typechecks import STANDIN_TYPES, b_isinstance, b_issubclass, standin_type, type_name

if TYPE_CHECKING:
    from ..core_types import Args, Frame, Kwargs
    from .lookup import Entry
    from .objects import Code, Signal

HOST_DESCRIPTORS: dict[type, int] = {types.WrapperDescriptorType: 1, types.MethodDescriptorType: 1,
                                     types.ClassMethodDescriptorType: 1}
"""Types of the unbound methods of host classes (used as a set).  When one of
them rejects an interpreted instance, `call` retries it on the instance's
native part.  (Not `type(object.__init__)`: when boros runs itself,
`object.__init__` is the emulation obj_init, an interpreted function.)"""

VALUE_TYPES: dict[type, int] = {str: 1, bytes: 1, int: 1, float: 1, complex: 1, tuple: 1, frozenset: 1}
"""Host value types (used as a set) whose constructors and methods check the
exact type of their arguments, and never call back into interpreted code.
When one rejects an interpreted instance of a subclass of a host type,
`call` retries it with the instance's native part."""

BUILTIN_METHOD: type = type(''.join)
"""The type of the bound methods of host objects, such as 'a,b'.split."""


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def call(f: Any, args: Args, kw: Kwargs) -> Any:
    """Call any callable with a tuple of positional arguments and a dict of
    keyword arguments (or None).

    This is the interpreter's universal call operation.  The checks are
    ordered by how often each kind of callee occurs.  Compiled call sites
    test for an interpreted Function themselves (see compiler/calls.py) and
    only come here for the other cases.
    """
    t: type = type(f)
    if t is Function:
        return invoke(f, args, kw)
    if t is Method:
        func: Any = f.im_func
        args = (f.im_self,) + args
        if type(func) is Function:
            return invoke(func, args, kw)
        return call(func, args, kw)
    if t is Class:
        return instantiate(f, args, kw)
    if t is Instance:
        return call_instance(f, args, kw)
    if f is type or f is super:
        return call_emulated_builtin(f, args, kw)
    try:
        if kw:
            return f(*args, **kw)
        return f(*args)
    except (TypeError, ValueError) as x:
        # A host callable rejecting interpreted objects that stand for host
        # ones, e.g. Exception.__init__ called on an interpreted instance.
        r: Any = retry_on_native(f, args, kw, x)
        if r is MISSING:
            raise
        return r


def type_of(x: Any) -> Any:
    """type(x): the class of x, which for an instance of an interpreted
    class is that interpreted Class (and for an interpreted function the
    host type it stands for)."""
    t: type = type(x)
    if t is Instance:
        return x.cls
    if t in STANDIN_TYPES:
        return standin_type(x)
    return t


def call_with_natives(f: Any, args: Args, kw: Kwargs) -> Any:
    """Retry host callable f, which rejected `args` with a TypeError, with
    native parts in place of interpreted instances where Python would have
    accepted an instance of a subclass of a host type.  Returns MISSING if
    there is nothing to retry (the caller re-raises the TypeError)."""
    if not args:
        return MISSING
    if type(args[0]) is Instance and args[0].native is not None and type(f) in HOST_DESCRIPTORS:
        # an unbound method of a host base class (e.g. Exception.__init__)
        # called on an interpreted instance: apply it to the native part
        return call_on_native(f, args, kw)
    if not takes_values(f):
        return MISSING
    a: list[Any] = [x.native if type(x) is Instance and x.native is not None else x for x in args]
    if all(x is y for x, y in zip(a, args)):
        return MISSING
    if kw:
        return f(*a, **kw)
    return f(*a)


def takes_values(f: Any) -> bool:
    """Whether f is the constructor or a bound method of one of VALUE_TYPES
    (`int(s)`, `'abc'.find(s)`)."""
    t: type = type(f)
    if t is type:
        return f in VALUE_TYPES
    return t is BUILTIN_METHOD and type(f.__self__) in VALUE_TYPES


def retry_on_native(f: Any, args: Args, kw: Kwargs, x: Exception) -> Any:
    """Retry a call of host callable f that raised x (a TypeError or
    ValueError) because it was given interpreted objects: an unbound method
    of a host base class applied to an interpreted instance or a host value
    method given such instances (see call_with_natives), a host exception
    class's __new__ applied to an
    interpreted subclass (Exception.__new__(cls), which native_new
    implements), or an exception group created from interpreted exceptions.
    Returns MISSING when none of these is the case."""
    if not args:
        return MISSING
    if type(x) is ValueError:
        return new_exception_group(f, args, kw)
    a0: Any = args[0]
    if type(a0) is Class and is_host_exception_new(f, a0):
        return native_new(*args, **(kw or {}))
    return call_with_natives(f, args, kw)


def new_exception_group(f: Any, args: Args, kw: Kwargs) -> Any:
    """ExceptionGroup(message, exceptions) (f is a host exception group
    class) where exceptions include interpreted exceptions, which the host
    class accepts only as their native parts; MISSING if that is not it."""
    if kw or len(args) != 2 or not (isinstance(f, type) and issubclass(f, BaseExceptionGroup)):
        return MISSING
    items: Any = args[1]
    if type(items) is not list and type(items) is not tuple:
        return MISSING
    natives: list[Any] = [x.native if type(x) is Instance and isinstance(x.native, BaseException) else x
                          for x in items]
    if all(n is x for n, x in zip(natives, items, strict=True)):
        return MISSING
    return f(args[0], natives)


def is_host_exception_new(f: Any, cls: Class) -> bool:
    """Whether f is the __new__ of a host exception class that is a base of
    interpreted class cls."""
    owner: Any = getattr(f, '__self__', None)
    return (getattr(f, '__name__', None) == '__new__' and isinstance(owner, type) and issubclass(owner, BaseException)
            and owner in cls.mro)


def call_on_native(f: Any, args: Args, kw: Kwargs) -> Any:
    """Call host method f with the native part of the instance args[0] in
    place of the instance itself."""
    if f is EXC_REPR and len(args) == 1 and not kw:
        return exc_repr(args[0].cls.__name__, args[0].native.args)
    a: Args = (args[0].native,) + args[1:]
    if kw:
        return f(*a, **kw)
    return f(*a)


def call_emulated_builtin(f: Any, args: Args, kw: Kwargs) -> Any:
    """Call `type` or `super`, whose host versions do not understand
    interpreted classes and instances."""
    if f is type:
        if len(args) == 1 and not kw:
            return type_of(args[0])
        return call_type(args, kw)
    if not args:
        raise RuntimeError('super(): no arguments')
    return b_super(*args)


def b_super(thisclass: Any, obj: Any = None) -> Super:
    """super(type) and super(type, obj) called explicitly, with CPython's
    checks: obj must be an instance or a subclass of type.  Without obj (or
    with None) the super object is unbound."""
    if type(thisclass) is not Class and not isinstance(thisclass, type):
        raise TypeError(f'super() argument 1 must be a type, not {type_name(thisclass)}')
    if obj is not None and not super_obj_ok(thisclass, obj):
        what: str = f'type {obj.__name__}' if is_class(obj) else f'instance of {type_name(obj)}'
        raise TypeError(f'super(type, obj): obj ({what}) is not an instance or subtype of type '
                        f'({thisclass.__name__}).')
    return Super(thisclass, obj)


def is_class(x: Any) -> bool:
    """Whether x is a class, interpreted or host."""
    return type(x) is Class or isinstance(x, type)


def super_obj_ok(thisclass: Any, obj: Any) -> bool:
    """Whether super(thisclass, obj) is allowed: obj is an instance of
    thisclass or a subclass of it."""
    if is_class(obj) and b_issubclass(obj, thisclass):
        return True
    return b_isinstance(obj, thisclass)


def call_instance(f: Instance, args: Args, kw: Kwargs) -> Any:
    """Call an instance of an interpreted class that defines __call__."""
    from .attributes import bind_value
    e: Entry = lookup(f.cls, '__call__')
    if e[0] is K_MISSING or e[0] is K_NODICT:
        raise TypeError(f"'{f.cls.__name__}' object is not callable")
    return call(bind_value(e[1], e[0], f, f.cls), args, kw)


def call_type(args: Args, kw: Kwargs) -> Any:
    """type(x) or type(name, bases, ns)."""
    from .classes import b_type
    if kw:
        return b_type(*args, **kw)
    return b_type(*args)


def call_descriptor(v: Any, k: Signal, inst: Instance, cls: Class, args: Args, kw: Kwargs) -> Any:
    """Bind class attribute v (of kind k) to inst and call it."""
    from .attributes import bind_value
    return call(bind_value(v, k, inst, cls), args, kw)


# ---------------------------------------------------------------------------
# Interpreted functions
# ---------------------------------------------------------------------------

def invoke(f: Function, args: Args, kw: Kwargs) -> Any:
    """Call an interpreted function.

    Fast path: when f has only plain positional parameters (and is not a
    generator, a coroutine or a user of the class cell; `f.fastn` is then
    its parameter count) and is called with exactly that many positional
    arguments, the frame is built straight from the arguments.

    Otherwise `bind_args` builds the frame.  Calling a generator,
    coroutine or async generator function does not run its body: it
    returns the generator, a host coroutine running it, or an
    async_generator (see coroutines.py).  Exceptions escaping the body get
    this call recorded in their interpreted traceback.
    """
    if kw is None and len(args) == f.fastn:
        fr: Frame = dict(zip(f.code.params, args))
        fr['.up'] = f.closure
        try:
            return f.body(fr)
        except BaseException as e:
            annotate_call(e, fr, f)
            raise
    code: Code = f.code
    fr = bind_args(f, code, args, kw)
    clo: Frame | None = f.closure
    if clo is not None:
        fr['.up'] = clo
    if code.uses_class:
        fr['.cls'] = f.classcell
    if code.is_gen:
        g: Any = code.body(fr)
        if code.is_async:
            g = async_generator(g) if code.is_asyncgen else coroutine(AwaitBody(g))
        g.__name__ = code.name
        g.__qualname__ = code.qualname
        return g
    try:
        return code.body(fr)
    except BaseException as e:
        annotate(e, fr, code.line, code.name, code.filename)
        raise


# ---------------------------------------------------------------------------
# Argument binding
# ---------------------------------------------------------------------------

def bind_args(f: Function, code: Code, args: Args, kw: Kwargs) -> Frame:
    """Build the initial frame for a call of f, following CPython's rules.

    In order: surplus positional arguments go to *args (or are an error),
    positional arguments bind to the leading parameters, keyword arguments
    bind by name (or go to **kwargs), and parameters still unbound take
    their defaults.  Errors use CPython's messages.
    """
    fr: Frame = {}
    params: list[str] = code.params
    argcount: int = code.argcount
    nargs: int = len(args)
    if nargs > argcount:
        if code.vararg is None:
            raise too_many_error(f, code, args, kw)
        fr[code.vararg] = tuple(args[argcount:])
        nargs = argcount
    elif code.vararg is not None:
        fr[code.vararg] = ()
    i: int = 0
    while i < nargs:
        fr[params[i]] = args[i]
        i += 1
    kwdict: dict[str, Any] | None = None
    if code.kwarg is not None:
        kwdict = {}
        fr[code.kwarg] = kwdict
    if kw:
        bind_keywords(code, fr, kw, kwdict)
    if nargs < argcount:
        bind_defaults(f, code, fr, nargs)
    if code.kwonly:
        bind_kwonly_defaults(f, code, fr)
    return fr


def bind_keywords(code: Code, fr: Frame, kw: dict[str, Any], kwdict: dict[str, Any] | None) -> None:
    """Bind keyword arguments to the parameters of the same name, or else
    store them in the **kwargs dict kwdict (None if there is none)."""
    kwnames: set[str] = code.kwnames
    for k, v in kw.items():
        if k in kwnames:
            if k in fr:
                raise multiple_values(code, k)
            fr[k] = v
        elif kwdict is not None:
            kwdict[k] = v
        else:
            raise bad_keywords(code, kw, k)


def bind_defaults(f: Function, code: Code, fr: Frame, nargs: int) -> None:
    """Give the positional parameters after the first nargs that were not
    passed by keyword their default values."""
    params: list[str] = code.params
    argcount: int = code.argcount
    defaults: tuple[Any, ...] = f.defaults or ()
    first_default: int = argcount - len(defaults)
    i: int = nargs
    while i < argcount:
        p: str = params[i]
        if p not in fr:
            if i < first_default:
                missing: list[str] = [q for q in params[i:first_default] if q not in fr]
                raise missing_arguments(f, 'positional', missing)
            fr[p] = defaults[i - first_default]
        i += 1


def bind_kwonly_defaults(f: Function, code: Code, fr: Frame) -> None:
    """Give the keyword-only parameters that were not passed their default
    values."""
    kwd: dict[str, Any] | None = f.kwdefaults
    for p in code.kwonly:
        if p not in fr:
            if kwd is None or p not in kwd:
                missing: list[str] = [q for q in code.kwonly if q not in fr and (kwd is None or q not in kwd)]
                raise missing_arguments(f, 'keyword-only', missing)
            fr[p] = kwd[p]


# Error messages for bad calls (cold paths)

def plural(n: int) -> str:
    """The plural suffix for a count of n things."""
    return '' if n == 1 else 's'


def join_names(names: list[str]) -> str:
    """Quote and join parameter names the way CPython's messages do:
    'a', 'a' and 'b', or 'a', 'b', and 'c'."""
    quoted: list[str] = [f"'{n}'" for n in names]
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return quoted[0] + ' and ' + quoted[1]
    return ', '.join(quoted[:-1]) + ', and ' + quoted[-1]


def too_many_error(f: Function, code: Code, args: Args, kw: Kwargs) -> TypeError:
    """The error for passing more positional arguments than f takes (and
    no *args).  CPython binds the keyword arguments first, so a duplicate
    or unexpected keyword is reported instead if there is one."""
    if kw:
        fr: Frame = dict(zip(code.params, args))
        try:
            bind_keywords(code, fr, kw, {} if code.kwarg is not None else None)
        except TypeError as e:
            return e
    return too_many_positional(f, code, len(args), kw)


def too_many_positional(f: Function, code: Code, given: int, kw: Kwargs) -> TypeError:
    """The error for passing `given` positional arguments to a function
    that takes fewer and has no *args."""
    argcount: int = code.argcount
    ndef: int = len(f.defaults or ())
    if ndef:
        takes: str = f'from {argcount - ndef} to {argcount} positional arguments'
    else:
        takes = f'{argcount} positional argument{plural(argcount)}'
    kwgiven: int = len([k for k in kw if k in code.kwonly]) if code.kwonly and kw else 0
    if kwgiven:
        return TypeError(f'{code.qualname}() takes {takes} but {given} positional argument{plural(given)} '
                         f'(and {kwgiven} keyword-only argument{plural(kwgiven)}) were given')
    verb: str = 'was' if given == 1 else 'were'
    return TypeError(f'{code.qualname}() takes {takes} but {given} {verb} given')


def multiple_values(code: Code, name: str) -> TypeError:
    """The error for a parameter given both positionally and by keyword."""
    return TypeError(f"{code.qualname}() got multiple values for argument '{name}'")


def bad_keywords(code: Code, kw: dict[str, Any], first: str) -> TypeError:
    """The error for keyword argument `first` of kw, which matches no
    parameter (and there is no **kwargs).

    As in CPython, if any keyword names positional-only parameters, those
    are reported together, in parameter order; otherwise `first` is an
    unexpected keyword, and a similar parameter name is suggested.
    """
    given: list[str] = [p for p in code.params[:code.nposonly] if p in kw]
    if given:
        joined: str = ', '.join(given)
        return TypeError(f"{code.qualname}() got some positional-only arguments passed as keyword arguments: "
                         f"'{joined}'")
    hint: str = keyword_suggestion(first, code.params[code.nposonly:] + code.kwonly)
    return TypeError(f"{code.qualname}() got an unexpected keyword argument '{first}'{hint}")


def missing_arguments(f: Function, kind: str, names: list[str]) -> TypeError:
    """The error for required parameters (of the given kind) of f left
    unbound.  It names f by its __qualname__, which dataclasses sets on the
    functions it generates."""
    n: int = len(names)
    return TypeError(f'{f.__qualname__}() missing {n} required {kind} argument{plural(n)}: {join_names(names)}')


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

def instantiate(cls: Class, args: Args, kw: Kwargs) -> Any:
    """Call an interpreted class: create the object with __new__, then
    initialise it with __init__.

    In the usual case __new__ is object's, which just makes a fresh
    Instance (plus its native part when the class derives from a host type
    such as Exception).  As in CPython, __init__ is skipped when __new__
    returns something that is not an instance of cls.
    """
    e: Entry = lookup(cls, '__new__')
    if e[0] is K_EMU:
        inst: Any = Instance(cls)
        if cls.native is not None:
            make_native(inst, cls.native, args, kw)
    else:
        inst = call_new(cls, e, args, kw)
        if type(inst) is not Instance or not b_issubclass(inst.cls, cls):
            return inst
    ie: Entry = lookup(cls, '__init__')
    k: Signal = ie[0]
    if k is K_FUNC:
        r: Any = invoke(ie[1], (inst,) + args, kw)
        if r is not None:
            raise TypeError(f"__init__() should return None, not '{type_name(r)}'")
    elif k is K_EMU:
        if (args or kw) and e[0] is K_EMU:
            raise TypeError(f'{cls.__name__}() takes no arguments')
    else:
        init_other(cls, inst, k, ie[1], args, kw)
    return inst


def call_new(cls: Class, e: Entry, args: Args, kw: Kwargs) -> Any:
    """Call the __new__ found by class lookup entry e: cls.__new__(cls, *args, **kw).

    __new__ is stored as a staticmethod; one inherited from a host base
    class is replaced by `native_new`, which knows about interpreted
    classes.
    """
    newf: Any = e[1]
    if e[0] is K_STATIC:
        newf = newf.__func__
    elif e[0] is K_NATIVE:
        newf = native_new
    return call(newf, (cls,) + args, kw)


def init_other(cls: Class, inst: Instance, k: Signal, v: Any, args: Args, kw: Kwargs) -> None:
    """Run an __init__ (class attribute v of kind k) that is not an
    interpreted function: a host base class's __init__ is applied to the
    native part; anything else is bound like any attribute and called."""
    if k is K_NATIVE:
        if inst.native is not None:
            if kw:
                inst.native.__init__(*args, **kw)
            else:
                inst.native.__init__(*args)
    else:
        call_descriptor(v, k, inst, cls, args, kw)


def make_native(inst: Instance, base: type, args: Args, kw: Kwargs) -> None:
    """Create the native part of inst: an object of the host base class
    `base`.  A native exception remembers the instance it belongs to, so
    that catching it gives back the interpreted exception."""
    if issubclass(base, BaseException):
        n: Any = base.__new__(base, *args)
        setattr(n, INST_KEY, inst)
    elif base.__dictoffset__ != 0 and HOST_CLASSES and not issubclass(base, type):
        n = make_shadow_native(inst, base, args, kw)
    elif kw:
        n = base.__new__(base, *args, **kw)
    else:
        n = base.__new__(base, *args)
    inst.native = n


SHADOW_SKIP: dict[str, int] = {'__init__': 1, '__new__': 1, '__getattribute__': 1, '__getattr__': 1,
                               '__setattr__': 1, '__delattr__': 1, '__init_subclass__': 1, '__class_getitem__': 1,
                               '__set_name__': 1, '__del__': 1, '__dict__': 1, '__weakref__': 1, '_boros_inst': 1}
"""Attributes a shadow class does not forward: the methods of object
creation and of attribute access, the class-level hooks, and the attributes
that make up the shadow class's own layout."""


HOST_CLASSES: bool = hasattr(type('Probe', (), {}), '__basicsize__')
"""Whether type(name, bases, ns) makes genuine host classes, which shadow
classes must be.  It does not when boros runs inside boros, where it makes
classes of the outer interpreter; natives are then plain objects of their
host base class."""


def make_shadow_native(inst: Instance, base: type, args: Args, kw: Kwargs) -> Any:
    """The native part of inst when its host base class gives instances a
    __dict__ (a pure-Python class such as threading.Thread or
    logging.Handler, or Counter, OrderedDict, ...): an object of the
    shadow class of inst's class, whose attribute dict inst (which has no
    attributes yet) adopts as its own, so that what the base class's code
    stores on self is an attribute of the interpreted object and the other
    way round."""
    t: type = shadow_class(inst.cls, base)
    new: Any = base.__new__
    if new is object.__new__:
        # (which accepts no arguments for a class without an __init__)
        n: Any = new(t)
    elif kw:
        n = new(t, *args, **kw)
    else:
        n = new(t, *args)
    d: dict[str, Any] = n.__dict__
    inst.__dict__ = d
    inst.d = d
    if t is not base:
        n._boros_inst = inst
    return n


def shadow_class(cls: Class, base: type) -> type:
    """The shadow class of interpreted class cls deriving from host class
    `base`: a host subclass of base, named like cls, in which each
    attribute defined by the interpreted classes of the MRO stands for the
    interpreted one (see attributes.ShadowAttr).  The base class's own code
    (Thread.start calling self.run(), HTMLParser.feed calling
    self.handle_starttag(), repr() of an OrderedDict, ...) runs on the
    native part and so reaches the interpreted overrides.  It is made once
    and kept until the class changes.  If base cannot be subclassed so
    (its layout or its __init_subclass__ refuses), natives are made from
    base itself."""
    t: type | None = cls.shadow
    if t is None:
        try:
            t = make_shadow_class(cls, base)
        except TypeError:
            t = base
        cls.shadow = t
    return t


def make_shadow_class(cls: Class, base: type) -> type:
    """Create the shadow class of cls (see shadow_class).  An attribute set
    to None (such as `__hash__ = None`) stays None."""
    from .attributes import ShadowAttr
    ns: dict[str, Any] = {'__slots__': ('_boros_inst',), '__module__': cls.__module__,
                          '__qualname__': cls.__qualname__, '__new__': shadow_new(cls)}
    for k in cls.mro:
        if type(k) is not Class:
            break
        for name, v in k.ns.items():
            if name not in ns and name not in SHADOW_SKIP:
                ns[name] = None if v is None else ShadowAttr(cls, name)
    return type(base)(cls.__name__, (base,), ns)


def shadow_new(cls: Class) -> staticmethod[..., Any]:
    """The __new__ of the shadow class of cls: host code making an object of
    the class of a native part (UserList slicing calls
    self.__class__(data), ...) gets an instance of cls."""
    def new(t: Any, *args: Any, **kw: Any) -> Any:
        return instantiate(cls, args, kw or None)
    return staticmethod(new)


def native_new(cls: Any, *args: Any, **kw: Any) -> Any:
    """The __new__ of a host base class, as reached through
    super().__new__(cls) or inherited by an interpreted class."""
    if type(cls) is not Class:
        return cls.__new__(cls, *args, **kw)
    inst: Instance = Instance(cls)
    if cls.native is not None:
        make_native(inst, cls.native, args, kw or None)
    return inst
