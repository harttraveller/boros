"""Class attribute lookup along the MRO, with a per-class cache that also classifies
each attribute (plain value, function, property, descriptor, ...).

Looking up `name` on a class yields an Entry `(kind, value, owner)`: the kind
says how attribute access must treat the value (bind a function into a method,
call a property's getter, read a slot, ...), so the hot attribute paths in
attributes.py and the compiler only compare `kind` against these K_* markers
instead of re-examining the value on every access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .objects import Class, Function, Instance, Method, Signal, SlotDescriptor

if TYPE_CHECKING:
    from collections.abc import Callable

Entry = tuple[Signal, Any, Any]
"""A classified class attribute: (kind, value, class in the MRO that defines it).
The value and owner are None when the kind alone says it all (K_MISSING, ...)."""

# kinds of class attributes, as classified by kind_of() and find_attr()

# not defined anywhere in the MRO
K_MISSING: Signal = Signal('missing')


# not defined, and instances have no __dict__ (all __slots__)
K_NODICT: Signal = Signal('nodict')


# an ordinary value (number, string, class, None, ...)
K_PLAIN: Signal = Signal('plain')


# an interpreted function: becomes a bound Method on instances
K_FUNC: Signal = Signal('func')


K_STATIC: Signal = Signal('staticmethod')


K_CLASSM: Signal = Signal('classmethod')


K_PROP: Signal = Signal('property')


# a SlotDescriptor: the value lives in the instance's `sv` dict
K_SLOT: Signal = Signal('slot')


# an Instance whose class defines __set__ or __delete__ (a data descriptor)
K_IDATA: Signal = Signal('instance data descriptor')


# an Instance whose class defines only __get__
K_IGET: Signal = Signal('instance descriptor')


# an Instance whose class defines __set__ or __delete__ but not __get__: a
# data descriptor for assignment and deletion that reads like a plain value
K_ISET: Signal = Signal('instance data descriptor without __get__')


# a host object whose type defines __get__ and __set__/__delete__
K_HDATA: Signal = Signal('host data descriptor')


# a host object whose type defines only __get__
K_HGET: Signal = Signal('host descriptor')


# an attribute of a host base class (found in its __dict__)
K_NATIVE: Signal = Signal('native')


# one of the emulated methods of `object` (OBJECT_METHODS)
K_EMU: Signal = Signal('object method')


# `__class__`, which `object` provides for every instance
K_CLASS: Signal = Signal('__class__')


# `__dict__`, which `object` provides for instances that have one
K_DICT: Signal = Signal('__dict__')


# the class overrides __getattribute__: every access goes to the hook
K_HOOK: Signal = Signal('__getattribute__')


# `__annotations__` of a base class: instances see it, but a class's own
# __annotations__ never comes from its bases
K_BASE_ANNOTATIONS: Signal = Signal('base class __annotations__')


MISSING_ENTRY: Entry = (K_MISSING, None, None)


# emulations of the host `object` type's methods, filled in by object_methods
OBJECT_METHODS: dict[str, Callable[..., Any]] = {}


NODICT_ENTRY: Entry = (K_NODICT, None, None)


DICT_ENTRY: Entry = (K_DICT, None, None)
# ids of the host functions that replace builtins (isinstance, getattr, ...):
# like the builtins they stand for, they do not bind as methods when stored
# as class attributes (filled in by builtin_functions)
NONBINDING: dict[int, int] = {}


# types whose values are never descriptors (checked with one dict lookup)
PLAIN_TYPES: dict[type, int] = {int: 1, str: 1, float: 1, bool: 1, tuple: 1, list: 1, dict: 1, set: 1,
                                frozenset: 1, type(None): 1, bytes: 1, complex: 1, Class: 1, Method: 1}


def kind_of(v: Any) -> Signal:
    """Classify a class attribute value, deciding how attribute access on
    instances and classes must treat it.  The common kinds are tested first."""
    t: type = type(v)
    if t is Function:
        return K_FUNC
    if t in PLAIN_TYPES:
        return K_PLAIN
    if t is staticmethod:
        return K_STATIC
    if t is classmethod:
        return K_CLASSM
    if t is property:
        return K_PROP
    if t is SlotDescriptor:
        return K_SLOT
    if t is Instance:
        return instance_kind(v)
    if id(v) in NONBINDING:
        return K_PLAIN
    return host_kind(t)


def instance_kind(v: Instance) -> Signal:
    """Classify an Instance stored as a class attribute: it is a descriptor
    if its class defines __get__, __set__ or __delete__."""
    c: Class = v.cls
    if has_class_attr(c, '__set__') or has_class_attr(c, '__delete__'):
        if not has_class_attr(c, '__get__'):
            return K_ISET
        return K_IDATA
    if has_class_attr(c, '__get__'):
        return K_IGET
    return K_PLAIN


def host_kind(t: type) -> Signal:
    """Classify a host object of type `t` stored as a class attribute: it is a
    descriptor if its type defines __get__."""
    if hasattr(t, '__get__'):
        if hasattr(t, '__set__') or hasattr(t, '__delete__'):
            return K_HDATA
        return K_HGET
    return K_PLAIN


def find_attr(cls: Class, name: str) -> Entry:
    """Search the MRO of `cls` for attribute `name` (uncached).

    Interpreted classes are searched through their namespace dicts.  `object`
    itself is emulated (K_CLASS / K_EMU, and K_DICT for the `__dict__` of
    instances that have one), and other host types are searched through
    their __dict__ (K_NATIVE)."""
    for k in cls.mro:
        if type(k) is Class:
            ns: dict[str, Any] = k.ns
            if name in ns:
                v: Any = ns[name]
                if name == '__annotations__' and k is not cls:
                    return (K_BASE_ANNOTATIONS, v, k)
                return (kind_of(v), v, k)
        elif k is object:
            if name == '__class__':
                return (K_CLASS, None, k)
            f: Callable[..., Any] | None = OBJECT_METHODS.get(name)
            if f is not None:
                return object_entry(cls, name, f)
            break
        else:
            hd: Any = k.__dict__
            if name in hd:
                return (K_NATIVE, hd[name], k)
    return missing_entry(cls, name)


def missing_entry(cls: Class, name: str) -> Entry:
    """The entry for a name no class on the MRO of cls defines: the
    instance's own __dict__ (K_DICT), or nothing (K_NODICT for instances of
    __slots__ classes, which cannot store it either, else K_MISSING)."""
    if cls.dictless:
        return NODICT_ENTRY
    if name == '__dict__':
        return DICT_ENTRY
    return MISSING_ENTRY


def object_entry(cls: Class, name: str, f: Callable[..., Any]) -> Entry:
    """The entry for the emulated method f of `object` found by looking up
    `name` on cls.  An abstract class (one with abstract methods left, see
    classes.setup_abc) gets a __new__ that refuses to instantiate it."""
    if name == '__new__' and cls.ns.get('__abstractmethods__'):
        return (K_STATIC, staticmethod(abstract_new), object)
    return (K_EMU, f, object)


def abstract_new(cls: Class, *args: Any, **kw: Any) -> Any:
    """The __new__ of an abstract class."""
    raise abstract_class_error(cls)


def abstract_class_error(cls: Class) -> TypeError:
    """The error for instantiating an abstract class."""
    names: list[str] = sorted(cls.ns['__abstractmethods__'])
    quoted: str = ', '.join([f"'{n}'" for n in names])
    return TypeError(f"Can't instantiate abstract class {cls.__name__} without an implementation for abstract "
                     f"method{'s' if len(names) > 1 else ''} {quoted}")


def lookup(cls: Class, name: str) -> Entry:
    """Find and classify attribute `name` of class `cls`, using the class's cache
    (which invalidate() clears whenever a class in the hierarchy changes)."""
    e: Entry | None = cls.cache.get(name)
    if e is None:
        e = find_attr(cls, name)
        cls.cache[name] = e
    return e


def afill(cls: Class, name: str) -> Entry:
    """Fill the attribute-access cache entry for `name` after a miss.  It is
    the same as lookup() unless __getattribute__ is overridden, in which case
    every access goes to the hook."""
    if cls.gethook is None:
        return lookup(cls, name)
    e: Entry = (K_HOOK, cls.gethook, None)
    cls.acache[name] = e
    return e


def has_special(o: Instance, name: str) -> bool:
    """Whether the class of instance `o` defines special method `name`."""
    k: Signal = lookup(o.cls, name)[0]
    return k is not K_MISSING and k is not K_NODICT


def has_class_attr(cls: Class, name: str) -> bool:
    """Whether attribute `name` is defined somewhere on the MRO of class `cls`
    (lookup() reports a name a __slots__ class lacks as K_NODICT, not
    K_MISSING)."""
    k: Signal = lookup(cls, name)[0]
    return k is not K_MISSING and k is not K_NODICT
