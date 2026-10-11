"""The interpreter's object types: functions, methods, classes, instances, super objects.

This is the bottom layer of the runtime.  In an interpreted program every `def`
or `lambda` produces a `Function`, every `class` statement a `Class`, and
calling a `Class` produces an `Instance`.  Attribute lookup, calls and
special-method forwarding for these objects live in higher layers (lookup,
attributes, calls, protocols).

The host-interop dunders below (`Function.__call__`, `Class.__getattr__`, ...) let
host code - the standard library, builtins such as `sorted(key=...)` - use
interpreted objects as if they were ordinary Python objects.  They import the
higher layers lazily, inside the method, to avoid import cycles.
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from typing import Self

    from ..core_types import ExprFn, Frame
    from ..syntax import Arguments, Scope
    from .lookup import Entry


class Signal:
    """A unique marker object with a readable repr.

    Compiled statements return BREAK, CONTINUE or RETURN (or None) to tell the
    enclosing loop or function body how control leaves them; MISSING stands
    for "no value" where None is itself a legitimate value.  The attribute
    kinds in lookup (K_FUNC, K_PROP, ...) are Signals too."""

    def __init__(self, name: str) -> None:
        self.name: str = name

    def __repr__(self) -> str:
        return f'<{self.name}>'


BREAK: Signal = Signal('break')


CONTINUE: Signal = Signal('continue')


RETURN: Signal = Signal('return')


MISSING: Signal = Signal('missing')


class Code:
    """Compiled function body plus everything needed to bind arguments.

    One Code is created per `def` or `lambda` when the source is compiled; each
    execution of the `def` statement then wraps it in a new Function carrying
    that execution's defaults and enclosing frame.  The co_* attributes are
    those of a host code object that programs commonly inspect."""

    # the line of the `def` (set by the compiler)
    co_firstlineno: int = 0
    # constant annotations as (name, value) pairs, from which __annotations__
    # is made when first read (see compiler.definitions.annotation_closures)
    annotations: tuple[tuple[str, Any], ...] = ()

    def __init__(self, name: str, qualname: str, filename: str, line: int, args: Arguments, body: ExprFn,
                 scope: Scope, doc: str | None) -> None:
        self.name: str = name
        self.qualname: str = qualname
        self.filename: str = filename
        self.line: int = line
        # positional parameters (positional-only ones first), in order
        self.params: list[str] = args.posonly + args.args
        self.argcount: int = len(self.params)
        self.nposonly: int = len(args.posonly)
        self.kwonly: list[str] = args.kwonly
        self.vararg: str | None = args.vararg
        self.kwarg: str | None = args.kwarg
        # names that may be passed by keyword
        self.kwnames: set[str] = set(args.args + args.kwonly)
        # runs the body in a bound frame (for a generator: returns a host generator)
        self.body: ExprFn = body
        self.is_gen: bool = scope.is_gen
        self.is_async: bool = scope.is_async
        # an async def containing yield: calls return an async generator
        self.is_asyncgen: bool = scope.is_async and scope.has_yield
        # the body uses __class__ (zero-argument super()), so calls need the class cell
        self.uses_class: bool = scope.uses_class
        self.doc: str | None = doc
        # Number of positional arguments for the fast call path, which builds
        # the frame straight from the parameter names; -1 if the signature
        # needs full argument binding (*args, **kwargs or keyword-only).
        self.fastn: int = self.argcount if self.vararg is None and self.kwarg is None and not self.kwonly else -1
        # For introspection: the free variables (name -> number of '.up' links
        # to the frame owning it), the other names the body binds, and
        # whether the function is nested in another one.
        self.freevars: dict[str, int] = scope.freevars
        self.localnames: set[str] = scope.assigned
        if scope.globals or scope.nonlocals:
            self.localnames = scope.assigned - scope.globals - scope.nonlocals
        self.nested: bool = enclosing_function(scope) is not None

    co_name = property(lambda self: self.name)
    co_qualname = property(lambda self: self.qualname)
    co_filename = property(lambda self: self.filename)
    co_argcount = property(lambda self: self.argcount)
    co_posonlyargcount = property(lambda self: self.nposonly)
    co_kwonlyargcount = property(lambda self: len(self.kwonly))
    co_varnames = property(lambda self: introspect('code_varnames', self))
    co_freevars = property(lambda self: tuple(sorted(self.freevars)))
    co_flags = property(lambda self: introspect('code_flags', self))


def enclosing_function(scope: Scope) -> Scope | None:
    """The scope of the function that the code of `scope` is nested in, if any."""
    p: Scope | None = scope.parent
    while p is not None and p.kind != 'function':
        p = p.parent
    return p


def introspect(what: str, obj: Any) -> Any:
    """introspection.<what>(obj): the attributes that programs read to
    inspect functions (__closure__, __signature__, co_varnames, ...) are
    computed there, in a module loaded only when one of them is first read."""
    from . import introspection
    return getattr(introspection, what)(obj)


def exit_callback_args(args: tuple[Any, ...]) -> tuple[Any, ...]:
    """Arguments (exc_type, exc, traceback) passed by host code calling an
    interpreted function, as exit callbacks get them: the exception is
    mapped to the interpreted one it stands for (see errors.exc_triple)."""
    from .errors import exc_triple
    return exc_triple(args)


def _get_defaults(f: Function) -> tuple[Any, ...] | None:
    """Getter of Function.__defaults__."""
    return f.defaults


def _set_defaults(f: Function, v: tuple[Any, ...] | None) -> None:
    """Setter of Function.__defaults__."""
    if v is not None and not isinstance(v, tuple):
        raise TypeError('__defaults__ must be set to a tuple object')
    f.defaults = v


def _del_defaults(f: Function) -> None:
    """Deleter of Function.__defaults__ (which then is None)."""
    f.defaults = None


def _get_kwdefaults(f: Function) -> dict[str, Any] | None:
    """Getter of Function.__kwdefaults__."""
    return f.kwdefaults


def _set_kwdefaults(f: Function, v: dict[str, Any] | None) -> None:
    """Setter of Function.__kwdefaults__."""
    if v is not None and not isinstance(v, dict):
        raise TypeError('__kwdefaults__ must be set to a dict object')
    f.kwdefaults = v


def _get_name(f: Function) -> str:
    """Getter of Function.__name__."""
    return f._name


def _set_name(f: Function, v: Any) -> None:
    """Setter of Function.__name__, which must be a string."""
    if not isinstance(v, str):
        raise TypeError('__name__ must be set to a string object')
    f._name = v


def _get_doc(f: Function) -> Any:
    """Getter of Function.__doc__."""
    return f._doc


def _set_doc(f: Function, v: Any) -> None:
    """Setter of Function.__doc__."""
    f._doc = v


def _get_module(f: Function) -> Any:
    """Getter of Function.__module__."""
    return f._module


def _set_module(f: Function, v: Any) -> None:
    """Setter of Function.__module__."""
    f._module = v


def _del_kwdefaults(f: Function) -> None:
    """Deleter of Function.__kwdefaults__ (which then is None)."""
    f.kwdefaults = None


def _get_annotations(f: Function) -> dict[str, Any]:
    """Getter of Function.__annotations__: the annotations evaluated when
    the `def` ran, or else a dict made (once) from the constant annotations
    of the code."""
    try:
        return f.annotations
    except AttributeError:
        pass
    a: dict[str, Any] = dict(f.code.annotations)
    f.annotations = a
    return a


def _set_annotations(f: Function, v: dict[str, Any] | None) -> None:
    """Setter of Function.__annotations__ (None stands for a new empty dict)."""
    if v is None:
        v = {}
    elif not isinstance(v, dict):
        raise TypeError('__annotations__ must be set to a dict object')
    f.annotations = v


def _del_annotations(f: Function) -> None:
    """Deleter of Function.__annotations__, which then reads as an empty dict."""
    f.annotations = {}


class Function:
    """An interpreted function: a Code object plus the values captured when
    its `def` (or `lambda`) was executed.

    `closure` is the frame of the innermost enclosing function, or None at
    module level (stored as '.up' in each call's frame so that free variables
    can be found), `classcell` the one-element list holding `__class__` for
    zero-argument super(), and `defaults` / `kwdefaults` the evaluated default
    values.  `body`, `fastn`, `p1` and `p2` are copied out of the Code so the
    call fast paths need fewer lookups."""

    __slots__ = (
        '__dict__',
        '__qualname__',
        '__weakref__',
        '_doc',
        '_module',
        '_name',
        'annotations',
        'body',
        'classcell',
        'closure',
        'code',
        'defaults',
        'fastn',
        'globals',
        'kwdefaults',
        'p1',
        'p2',
    )

    def __init__(self, code: Code, globals: Frame, defaults: tuple[Any, ...] | None,
                 kwdefaults: dict[str, Any] | None, closure: Frame | None, classcell: list[Any] | None) -> None:
        self.code: Code = code
        self.globals: Frame = globals
        self.defaults: tuple[Any, ...] | None = defaults
        self.kwdefaults: dict[str, Any] | None = kwdefaults
        self.closure: Frame | None = closure
        self.classcell: list[Any] | None = classcell
        self.body: ExprFn = code.body
        # parameter names for the inlined one- and two-argument call paths
        self.p1: str | None = None
        self.p2: list[str] | None = None
        if code.is_gen or code.uses_class or code.is_async:
            # calls need full set-up (generator wrapping, class cell)
            self.fastn: int = -1
        else:
            self.fastn = code.fastn
            if code.fastn == 1:
                self.p1 = code.params[0]
            elif code.fastn == 2:
                self.p2 = code.params
        # kept out of the function's __dict__, which holds only the program's
        # own attributes: __name__, __doc__ and __module__ are properties
        self._name: str = code.name
        self.__qualname__: str = code.qualname
        self._doc: str | None = code.doc
        # the module name, or None
        self._module: Any = globals.get('__name__')

    # host code (e.g. sorted(key=f)) calling an interpreted function
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        from .calls import invoke
        if len(args) == 3 and isinstance(args[1], BaseException):
            args = exit_callback_args(args)
        if kwargs:
            return invoke(self, args, kwargs)
        return invoke(self, args, None)

    def __repr__(self) -> str:
        return f'<function {self.__qualname__} at 0x{id(self):x}>'

    # functions are atomic for the copy module, like host functions
    def __copy__(self) -> Function:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Function:
        return self

    # functions are descriptors: host code (functools.singledispatchmethod,
    # a host class holding an interpreted function, ...) binds them
    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            return self
        return Method(self, obj)

    __code__ = property(lambda self: self.code)
    __globals__ = property(lambda self: self.globals)
    __closure__ = property(lambda self: introspect('closure_cells', self))
    __defaults__ = property(_get_defaults, _set_defaults, _del_defaults)
    __kwdefaults__ = property(_get_kwdefaults, _set_kwdefaults, _del_kwdefaults)
    __name__ = property(_get_name, _set_name)
    # (cast: the type checker expects a dict here)
    __annotations__ = cast(Any, property(_get_annotations, _set_annotations, _del_annotations))
    # inspect.signature() asks for this before introspecting the object
    __signature__ = property(lambda self: introspect('function_signature', self), lambda self, v: set_signature(self, v))


# type(f).__name__ is 'function', as in CPython
Function.__name__ = 'function'
# (set here: in the class body, these names hold the class's own values)
Function.__doc__ = cast(Any, property(_get_doc, _set_doc))
Function.__module__ = cast(Any, property(_get_module, _set_module))


def method_doc(m: Method) -> Any:
    """The docstring of bound method m: that of its function."""
    from .attributes import getattr_any
    return getattr_any(m.im_func, '__doc__')


def method_annotations(m: Method) -> Any:
    """The annotations of bound method m: those of its function."""
    from .attributes import getattr_any
    return getattr_any(m.im_func, '__annotations__')


class Method:
    """A function bound to an object: the value of `obj.method`.

    Calling it calls `im_func` with `im_self` prepended to the arguments.
    Attributes it does not define itself, such as `__name__`, are those of
    the function."""

    __slots__ = ('im_func', 'im_self')

    # Interpreted programs read `__doc__` from this host class, so the
    # docstring above must not leak into them: a bound method's docstring
    # is its function's, and so are its annotations.  (No class-level
    # annotations here: they would give the host class an __annotations__
    # dict that shadows the function's.)
    __doc__ = cast(Any, property(method_doc))
    __annotations__ = cast(Any, property(method_annotations))

    def __init__(self, func: Any, obj: Any) -> None:
        self.im_func: Any = func
        self.im_self: Any = obj

    # host code calling a bound method
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        from .calls import call
        if len(args) == 3 and isinstance(args[1], BaseException):
            args = exit_callback_args(args)
        return call(self.im_func, (self.im_self,) + args, kwargs or None)

    # bound methods are equal when they bind the same function to the same object
    def __eq__(self, other: object) -> bool:
        return type(other) is Method and other.im_func is self.im_func and other.im_self is self.im_self

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((id(self.im_func), id(self.im_self)))

    def __repr__(self) -> str:
        name: Any = getattr(self.im_func, '__qualname__', '?')
        return f'<bound method {name} of {self.im_self!r}>'

    # a bound method stored as a class attribute stays bound
    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        return self

    # attributes not defined here are those of the function
    def __getattr__(self, name: str) -> Any:
        from .attributes import getattr_any
        return getattr_any(self.im_func, name)

    # copying binds the function to the object (or to a deep copy of it)
    def __copy__(self) -> Method:
        return Method(self.im_func, self.im_self)

    def __deepcopy__(self, memo: dict[int, Any]) -> Method:
        import copy
        return Method(self.im_func, copy.deepcopy(self.im_self, memo))

    __func__ = property(lambda self: self.im_func)
    __self__ = property(lambda self: self.im_self)
    __signature__ = property(lambda self: introspect('method_signature', self))


# type(m).__name__ is 'method', as in CPython
Method.__name__ = 'method'
# m.__module__ is its function's (forwarded like the attributes Method lacks)
Method.__module__ = cast(Any, property(lambda self: self.__getattr__('__module__')))


def set_signature(f: Function, sig: Any) -> None:
    """Assigning f.__signature__ stores it in f's __dict__, as in CPython."""
    f.__dict__['__signature__'] = sig


class SlotDescriptor:
    """The class attribute created for each name in a class's `__slots__`.

    Instances keep slot values in their `sv` dict rather than `d`; attribute
    access recognizes this descriptor (kind K_SLOT) and reads or writes `sv`."""

    # Interpreted programs read `__doc__` from this host class, which (like
    # CPython's member descriptors) must have none.
    __doc__ = None

    def __init__(self, name: str, owner: str) -> None:
        self.name: str = name
        self.owner: str = owner

    def __repr__(self) -> str:
        return f"<member '{self.name}' of '{self.owner}' objects>"


# type(C.slot).__name__ is 'member_descriptor', as in CPython
SlotDescriptor.__name__ = 'member_descriptor'


class Class:
    """An interpreted class.  Its namespace dict is `ns`; `mro` is the
    method resolution order (interpreted classes and host types)."""

    def __init__(self, name: str, bases: tuple[Any, ...], ns: dict[str, Any]) -> None:
        self.__name__: str = name
        # __qualname__ belongs to the type, not to its namespace (as in CPython)
        self.__qualname__: str = ns.pop('__qualname__', name)
        # the module name, or None (Any: object declares __module__ as str)
        self.__module__: Any = ns.get('__module__')
        self.__bases__: tuple[Any, ...] = bases
        self.ns: dict[str, Any] = ns
        # interpreted classes deriving directly from this one, for cache invalidation
        self.subclasses: list[Class] = []
        # name -> classified attribute found along the MRO (see lookup.lookup)
        self.cache: dict[str, Entry] = {}
        # the cache used by instance attribute access: `cache` itself, or a
        # separate one when __getattribute__ is overridden (see compute_hooks)
        self.acache: dict[str, Entry] = self.cache
        # user-defined __getattribute__ / __setattr__ / __delattr__, or None
        self.gethook: Any = None
        self.sethook: Any = None
        self.delhook: Any = None
        # entries are interpreted Classes and host types
        self.mro: list[Any] = compute_mro(self, bases)
        # the host base class (e.g. Exception, dict) whose behaviour instances
        # need a native host object for, or None
        self.native: type | None = host_base(self.mro)
        # the host class standing for this one in host code, once made: the
        # subclass of `native` that natives are made from when it gives its
        # instances a __dict__ (see calls.shadow_class), or a subclass of the
        # host classes of the MRO when they are all stateless (host_class_of)
        self.shadow: type | None = None
        # instances have no __dict__ (all attributes must be slots)
        self.dictless: bool = False
        # for a class made by abc.ABCMeta (an abstract base class), the
        # classes registered as its virtual subclasses (see classes.setup_abc)
        self.abc_registry: list[Any] | None = None
        if '__slots__' in ns:
            self.dictless = declare_slots(name, bases, ns)
        for b in bases:
            if type(b) is Class:
                b.subclasses.append(self)
        compute_hooks(self)

    def __repr__(self) -> str:
        mod: Any = self.__module__
        if mod is None or mod == 'builtins':
            return f"<class '{self.__qualname__}'>"
        return f"<class '{mod}.{self.__qualname__}'>"

    # Host code calling, isinstance-checking or reading attributes of an
    # interpreted class goes through the runtime, like interpreted code does.
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        from .calls import instantiate
        return instantiate(self, args, kwargs or None)

    def __instancecheck__(self, obj: Any) -> bool:
        from .typechecks import b_isinstance
        return b_isinstance(obj, self)

    def __subclasscheck__(self, cls: Any) -> bool:
        from .typechecks import b_issubclass
        return b_issubclass(cls, self)

    # classes are atomic for the copy module, like host classes
    def __copy__(self) -> Class:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Class:
        return self

    def __getattr__(self, name: str) -> Any:
        from .attributes import class_getattr
        return class_getattr(self, name)

    # C | D, C | None: a union usable by isinstance()
    def __or__(self, other: Any) -> Any:
        from .typechecks import make_union
        return make_union(self, other)

    def __ror__(self, other: Any) -> Any:
        from .typechecks import make_union
        return make_union(other, self)

    # C[item]: __class_getitem__
    def __getitem__(self, item: Any) -> Any:
        from .attributes import class_getitem
        return class_getitem(self, item)

    # A class is not iterable (defining __getitem__ must not make the host
    # treat it as a sequence).
    def __iter__(self) -> Any:
        raise TypeError("'type' object is not iterable")

    # Host code reading C.__dict__ (collections.abc, inspect, ...) sees the
    # namespace, and C.__annotations__ the class's own annotations.  (cast:
    # the type checker expects dicts here.)
    __dict__ = cast(Any, property(lambda self: types.MappingProxyType(self.ns)))
    __annotations__ = cast(Any, property(lambda self: class_annotations(self),
                                         lambda self, v: set_class_annotations(self, v)))


def class_annotations(c: Class) -> Any:
    """Getter of Class.__annotations__ for host code."""
    from .attributes import class_getattr
    return class_getattr(c, '__annotations__')


def set_class_annotations(c: Class, v: Any) -> None:
    """Setter of Class.__annotations__ for host code."""
    from .attributes import class_setattr
    class_setattr(c, '__annotations__', v)


def host_base(mro: list[Any]) -> type | None:
    """The first host type in an MRO, other than `object`, whose instances
    have state: the host class an interpreted class derives from, such as
    Exception or dict.  Stateless host classes (see stateless_host_class)
    need no native object; their methods run on the Instance itself."""
    for k in mro:
        if type(k) is not Class:
            if k is object:
                break
            if not stateless_host_class(k):
                return k
    return None


def stateless_host_class(k: type) -> bool:
    """Whether host class k adds no state to its instances: object's layout,
    no __dict__, and no __new__ or __init__ of its own (abc.ABC,
    typing.Generic, typing.Protocol, the collections.abc classes, ...).
    The __dict__ test, rather than `k.__init__ is object.__init__`, also
    works when boros runs itself, where object.__init__ is emulated."""
    if k.__basicsize__ != object.__basicsize__ or k.__dictoffset__ != 0:
        return False
    for b in k.__mro__:
        if b is not object and ('__new__' in b.__dict__ or '__init__' in b.__dict__):
            return False
    return True


def mangle(name: str, classname: str) -> str:
    """Private-name mangling: `__x` in class `_C` becomes `_C__x`."""
    if name[:2] == '__' and name[-2:] != '__':
        return '_' + classname.lstrip('_') + name
    return name


def gives_dict(base: Any) -> bool:
    """Whether instances of base class `base` have a __dict__ (which
    subclasses inherit even when they declare __slots__)."""
    if type(base) is Class:
        return not base.dictless
    return base is not object


def declare_slots(name: str, bases: tuple[Any, ...], ns: dict[str, Any]) -> bool:
    """Add a SlotDescriptor to the namespace `ns` of class `name` for each name in
    its `__slots__`.  Returns whether instances are dictless: true unless
    '__dict__' is a slot or a base class provides a __dict__."""
    dictless: bool = True
    slots: Any = ns['__slots__']
    if type(slots) is str:
        slots = [slots]
    for s in slots:
        if s == '__dict__':
            dictless = False
        elif s != '__weakref__':
            s = mangle(s, name)
            if s in ns:
                raise ValueError(f'{s!r} in __slots__ conflicts with class variable')
            ns[s] = SlotDescriptor(s, name)
    for b in bases:
        if gives_dict(b):
            dictless = False
    return dictless


def compute_mro(cls: Class, bases: tuple[Any, ...]) -> list[Any]:
    """The method resolution order of a new class, by C3 linearization:
    merge the bases' MROs and the list of bases, repeatedly taking the first
    head that does not appear in the tail of any other list."""
    check_duplicate_bases(bases)
    seqs: list[list[Any]] = [base_mro(b) for b in bases]
    seqs.append(list(bases))
    result: list[Any] = [cls]
    while True:
        seqs = [s for s in seqs if s]
        if not seqs:
            return result
        head: Any = c3_head(seqs)
        if head is None:
            raise TypeError('Cannot create a consistent method resolution order (MRO) for bases ' +
                            ', '.join([b.__name__ for b in bases]))
        result.append(head)
        for s in seqs:
            if s[0] is head:
                del s[0]


def check_duplicate_bases(bases: tuple[Any, ...]) -> None:
    """Reject a class statement that names the same base class twice."""
    for i, b in enumerate(bases):
        if b in bases[i + 1:]:
            raise TypeError(f'duplicate base class {b.__name__}')


def base_mro(b: Any) -> list[Any]:
    """A copy of the MRO of base class `b` (an interpreted class or a host type)."""
    if type(b) is Class:
        return list(b.mro)
    return list(b.__mro__)


def c3_head(seqs: list[list[Any]]) -> Any:
    """The first head of the (non-empty) lists in `seqs` that is not in the
    tail of any of them, or None if there is none (the MRO is inconsistent)."""
    for s in seqs:
        cand: Any = s[0]
        if not in_some_tail(cand, seqs):
            return cand
    return None


def in_some_tail(cand: Any, seqs: list[list[Any]]) -> bool:
    """Whether `cand` appears after the first element of one of `seqs`."""
    for s in seqs:
        if cand in s[1:]:
            return True
    return False


def compute_hooks(cls: Class) -> None:
    """Find the class's user-defined attribute hooks (__getattribute__,
    __setattr__, __delattr__) and pick the instance attribute cache to match."""
    cls.gethook = user_attr(cls, '__getattribute__')
    cls.sethook = user_attr(cls, '__setattr__')
    cls.delhook = user_attr(cls, '__delattr__')
    if cls.gethook is None:
        cls.acache = cls.cache
    else:
        cls.acache = {}


def user_attr(cls: Class, name: str) -> Any:
    """Attribute `name` if an interpreted class in the MRO defines it before
    the first host type, else None."""
    for k in cls.mro:
        if type(k) is Class:
            if name in k.ns:
                return k.ns[name]
        else:
            return None
    return None


def invalidate(cls: Class) -> None:
    """Forget cached attribute lookups of `cls` and its subclasses, after an
    attribute of the class was set or deleted."""
    cls.cache.clear()
    compute_hooks(cls)
    cls.acache.clear()
    cls.shadow = None
    for sub in cls.subclasses:
        invalidate(sub)


class Instance:
    """An instance of an interpreted class.  `d` holds its attributes,
    `sv` its __slots__ values, and `native` the host object standing in
    for a host base class (for example the real exception object when the
    class derives from Exception).

    `d` is the Instance's own host-level __dict__, so that host code setting
    attributes of an interpreted object (functools.update_wrapper,
    abc.abstractmethod, argparse, the __init__ of a host base class, ...)
    stores them where interpreted code finds them, and host code reads
    them back directly."""

    __slots__ = ('__dict__', '__weakref__', 'cls', 'd', 'native', 'sv')

    def __init__(self, cls: Class) -> None:
        self.cls: Class = cls
        self.d: dict[str, Any] = self.__dict__
        self.native: Any = None
        self.sv: dict[str, Any] | None = None

    # Host code reading `inst.__class__` (isinstance() with a host class or
    # an ABC, unittest's runner, ...) gets host_class_of(inst); type(inst)
    # is Instance all the same.
    @property
    def __class__(self) -> type[Self]:
        return host_class_of(self)

    @__class__.setter
    def __class__(self, value: type[object], /) -> None:
        raise TypeError('the class of an interpreted object cannot be set by host code')


def host_class_of(inst: Instance) -> type:
    """`inst.__class__` as host code reads it (isinstance() with a host
    class or an ABC, unittest's runner, ...): the shadow class of inst's
    native part; for a class whose host bases are all stateless mixins, a
    host subclass of them standing for it (see mixin_stand_in); otherwise
    Instance itself."""
    n: Any = inst.native
    if n is not None:
        t: type = type(n)
        return t if '_boros_inst' in t.__dict__ else Instance
    c: Class = inst.cls
    if c.native is not None:
        return Instance
    s: type | None = c.shadow
    if s is None:
        s = mixin_stand_in(c)
        c.shadow = s
    return s


def mixin_stand_in(c: Class) -> type:
    """A host class standing for class c in host code: a subclass, named
    like c, of the host classes on c's MRO other than object (all stateless
    mixins, as c has no native part); Instance if there are none or they
    cannot be combined."""
    bases: list[type] = []
    for k in c.mro:
        if type(k) is not Class and k is not object and not any(issubclass(b, k) for b in bases):
            bases.append(k)
    if not bases:
        return Instance
    try:
        return type(c.__name__, tuple(bases), {'__module__': c.__module__, '__qualname__': c.__qualname__})
    except TypeError:
        return Instance


class Super:
    """The object returned by super(): attribute lookups on it search the MRO
    of `objtype` starting after `thisclass`, binding the result to `obj`."""

    __slots__ = ('obj', 'objtype', 'thisclass')

    def __init__(self, thisclass: Any, obj: Any) -> None:
        self.thisclass: Any = thisclass
        self.obj: Any = obj
        # the class whose MRO is searched: obj's class, or obj itself if it is a class
        if type(obj) is Instance:
            self.objtype: Any = obj.cls
        elif type(obj) is Class or isinstance(obj, type):
            self.objtype = obj
        elif obj is None:
            # unbound: super(type)
            self.objtype = None
        else:
            self.objtype = type(obj)

    def __repr__(self) -> str:
        return f'<super: {self.thisclass!r}, {self.objtype!r}>'

    # host code reading an attribute through a super object
    def __getattr__(self, name: str) -> Any:
        from .attributes import super_getattr
        return super_getattr(self, name)


# type(super()).__name__ is 'super', as in CPython
Super.__name__ = 'super'
