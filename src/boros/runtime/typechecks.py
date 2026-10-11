"""isinstance/issubclass/callable for a world where classes may be interpreted.

A "class" here is either an interpreted Class or a host type.  An Instance is an
instance of exactly the classes in its class's MRO; an interpreted Class is
itself an instance of `type` (and `object`); everything else is a host object
and the host's own isinstance/issubclass decide.
"""

from __future__ import annotations

import types
from abc import ABCMeta
from typing import TYPE_CHECKING, Any

from .lookup import has_special
from .objects import Class, Function, Instance, Method

if TYPE_CHECKING:
    from types import NotImplementedType

FUNCTION_TYPES: dict[type, type] = {Function: types.FunctionType, Method: types.MethodType}
"""The host types that interpreted functions and bound methods stand for:
type(f) is types.FunctionType and type(obj.method) is types.MethodType."""

VIRTUAL_SUBCLASSES: bool = False
"""Whether an interpreted abstract base class has registered a virtual
subclass or defines __subclasshook__.  Until one does, only the MRO
decides isinstance() and issubclass() for interpreted classes."""


def allow_virtual_subclasses() -> None:
    """Note that interpreted abstract base classes may now have virtual
    subclasses (see VIRTUAL_SUBCLASSES)."""
    global VIRTUAL_SUBCLASSES
    VIRTUAL_SUBCLASSES = True


def type_name(x: Any) -> str:
    """The name of x's type as an interpreted program sees it, for error messages."""
    t: type = type(x)
    if t is Instance:
        return x.cls.__name__
    if t is Class:
        return 'type'
    if t is Function:
        return 'function'
    if t is Method:
        return 'method'
    return t.__name__


def type_name_of_class(c: Any) -> str:
    """The name of class `c` (interpreted or host)."""
    return c.__name__


STANDIN_TYPES: dict[type, int] = {Class: 1, Function: 1, Method: 1}
"""The host classes of interpreted objects whose type() is something else
(see standin_type), used as a set: one dict lookup tells type() whether
its argument needs that."""


def metaclass_of(c: Class) -> type:
    """type(c) for interpreted class c: abc.ABCMeta for an abstract base
    class (see classes.setup_abc), otherwise type."""
    return ABCMeta if c.abc_registry is not None else type


def standin_type(x: Any) -> type:
    """type(x) for an interpreted class, function or bound method (one of
    STANDIN_TYPES): its metaclass, types.FunctionType or types.MethodType."""
    t: type = type(x)
    if t is Class:
        return metaclass_of(x)
    return FUNCTION_TYPES[t]


def b_isinstance(x: Any, cls: Any) -> bool:
    """The isinstance() builtin: `cls` may be a class, a tuple of classes or
    a union type (`int | str`).

    Beyond the MRO, an abstract base class counts its virtual subclasses
    (registered ones, and for the collections.abc classes those passing the
    __subclasshook__), and an interpreted function or bound method is an
    instance of the host type it stands for (types.FunctionType, ...)."""
    tc: type = type(cls)
    if tc is tuple:
        for c in cls:
            if b_isinstance(x, c):
                return True
        return False
    tx: type = type(x)
    if tx is Instance:
        if tc is Class:
            return cls in x.cls.mro or (VIRTUAL_SUBCLASSES and abc_subclass(x.cls, cls))
        if tc is type:
            return cls in x.cls.mro
        return instance_isinstance(x, cls, tc)
    if tc is Class:
        # only Instances (and virtual subclasses) are instances of interpreted classes
        return VIRTUAL_SUBCLASSES and abc_subclass(tx, cls)
    if tc is types.UnionType or tc is ClassUnion:
        return b_isinstance(x, cls.__args__)
    if tx in STANDIN_TYPES:
        return standin_isinstance(x, cls)
    return isinstance(x, cls)


def instance_isinstance(x: Instance, cls: Any, tc: type) -> bool:
    """isinstance(x, cls) for an interpreted instance x and a cls that is
    neither an interpreted class nor a plain host class (tc is its type):
    a host class with a metaclass (for an abstract base class such as
    collections.abc.Iterable, its __subclasshook__ also counts) or a union."""
    if isinstance(cls, type):
        return cls in x.cls.mro or (tc is ABCMeta and host_abc_subclass(x.cls, cls))
    if tc is types.UnionType or tc is ClassUnion:
        return b_isinstance(x, cls.__args__)
    raise TypeError('isinstance() arg 2 must be a type, a tuple of types, or a union')


def standin_isinstance(x: Any, cls: Any) -> bool:
    """isinstance(x, cls) for an interpreted class, function or bound method
    x, which is an instance of what type(x) gives (see standin_type)."""
    if type(x) is Class:
        return cls is type or cls is object or (cls is ABCMeta and x.abc_registry is not None)
    return isinstance(x, cls) or issubclass(FUNCTION_TYPES[type(x)], cls)


def b_issubclass(c: Any, cls: Any) -> bool:
    """The issubclass() builtin: `cls` may be a class, a tuple of classes or
    a union type."""
    tc: type = type(cls)
    if tc is tuple:
        for x in cls:
            if b_issubclass(c, x):
                return True
        return False
    if tc is types.UnionType or tc is ClassUnion:
        return b_issubclass(c, cls.__args__)
    if type(c) is Class:
        if tc is Class:
            return cls in c.mro or (VIRTUAL_SUBCLASSES and abc_subclass(c, cls))
        if isinstance(cls, type):
            return cls in c.mro or (tc is ABCMeta and host_abc_subclass(c, cls))
        raise TypeError('issubclass() arg 2 must be a class, a tuple of classes, or a union')
    if tc is Class:
        # a host class never derives from an interpreted one, but may be
        # registered as a virtual subclass of an abstract base class
        if not isinstance(c, type):
            raise TypeError('issubclass() arg 1 must be a class')
        return VIRTUAL_SUBCLASSES and abc_subclass(c, cls)
    return issubclass(c, cls)


class ClassUnion:
    """`X | Y` where X or Y is an interpreted class (the host's
    types.UnionType accepts only host types).  isinstance() and
    issubclass() accept it like a host union."""

    __slots__ = ('__args__',)

    def __init__(self, args: tuple[Any, ...]) -> None:
        self.__args__: tuple[Any, ...] = args

    def __or__(self, other: Any) -> Any:
        return make_union(self, other)

    def __ror__(self, other: Any) -> Any:
        return make_union(other, self)

    # unions are equal when they have the same members, in any order
    def __eq__(self, other: object) -> bool | NotImplementedType:
        if type(other) is not ClassUnion:
            return NotImplemented
        return set(self.__args__) == set(other.__args__)

    def __hash__(self) -> int:
        return hash(frozenset(self.__args__))

    def __repr__(self) -> str:
        return ' | '.join([union_member_repr(a) for a in self.__args__])


# type(A | B).__name__ is 'UnionType', as in CPython
ClassUnion.__name__ = 'UnionType'


def make_union(a: Any, b: Any) -> Any:
    """`a | b` where a or b is an interpreted class: the union of their
    members (unions are flattened, None stands for NoneType and duplicates
    are dropped), or NotImplemented if an operand cannot be in a union."""
    members: list[Any] = []
    for x in (a, b):
        parts: tuple[Any, ...] | None = union_members(x)
        if parts is None:
            return NotImplemented
        for m in parts:
            if m not in members:
                members.append(m)
    return ClassUnion(tuple(members))


def union_members(x: Any) -> tuple[Any, ...] | None:
    """The members x contributes to a union, or None if it cannot be in one."""
    if x is None:
        return (type(None),)
    t: type = type(x)
    if t is ClassUnion or t is types.UnionType:
        return x.__args__
    if t is Class or t is types.GenericAlias or isinstance(x, type):
        return (x,)
    return None


def union_member_repr(m: Any) -> str:
    """How a member of a union shows in its repr: `None`, a builtin class's
    name, `module.qualname`, or the repr of a generic alias."""
    if m is type(None):
        return 'None'
    if type(m) is not Class and not isinstance(m, type):
        return repr(m)
    mod: Any = m.__module__
    if mod is None or mod == 'builtins':
        return m.__qualname__
    return f'{mod}.{m.__qualname__}'


def abc_subclass(c: Any, cls: Class) -> bool:
    """Whether class c, which does not derive from it, is a virtual subclass
    of the interpreted abstract base class cls: its __subclasshook__ says
    so, or c is (a subclass of) a class registered with cls or with one of
    its subclasses.  Like ABCMeta.__subclasscheck__, without the caches."""
    if cls.abc_registry is None:
        return False
    from .attributes import class_getattr
    from .calls import call
    from .lookup import lookup
    if type(lookup(cls, '__subclasshook__')[2]) is Class:
        # a __subclasshook__ defined by an interpreted class
        r: Any = call(class_getattr(cls, '__subclasshook__'), (c,), None)
        if r is not NotImplemented:
            return bool(r)
    for r in cls.abc_registry or ():
        if c is r or b_issubclass(c, r):
            return True
    for sub in cls.subclasses:
        if sub.abc_registry is not None and abc_subclass(c, sub):
            return True
    return False


def host_abc_subclass(c: Class, cls: Any) -> bool:
    """issubclass(c, cls) for interpreted class c and a host abstract base
    class cls (for example collections.abc.Iterable) that is not in its
    MRO: cls.__subclasshook__ decides (those of collections.abc look for
    methods in the namespaces along c.__mro__), else whether a host base
    of c is a subclass of cls."""
    r: Any = cls.__subclasshook__(c)
    if r is not NotImplemented:
        return bool(r)
    for k in c.mro:
        if type(k) is not Class and k is not object and issubclass(k, cls):
            return True
    return False


def b_callable(x: Any) -> bool:
    """The callable() builtin: an Instance is callable if its class defines __call__."""
    if type(x) is Instance:
        return has_special(x, '__call__')
    return callable(x)


def is_iterable_type(v: Any) -> bool:
    """Whether the type of v supports iteration: it defines __iter__, or
    __getitem__ without being a dict (CPython's `tp_iter != NULL ||
    PySequence_Check(v)`).  A TypeError raised while iterating such a value
    propagates unchanged; for any other value, star-unpacking and
    destructuring report that the value is not iterable."""
    if type(v) is Instance:
        return has_special(v, '__iter__') or has_special(v, '__getitem__')
    t: type = type(v)
    return getattr(t, '__iter__', None) is not None or (getattr(t, '__getitem__', None) is not None
                                                        and not issubclass(t, dict))
