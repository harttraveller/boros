"""Attribute access (get/set/delete) on instances, classes and super objects.

Reading `o.name` from an interpreted Instance follows CPython's
object.__getattribute__:

1. look `name` up along the class's MRO (`lookup`, which caches the result
   together with its *kind*: plain value, function, property, slot, ...);
2. a data descriptor found there (property, slot, an object with __set__)
   wins;
3. otherwise the instance's own dict `o.d`;
4. otherwise the class attribute, bound to the instance if it is a
   function or other descriptor (`bind_value`);
5. otherwise the class's __getattr__ hook, or AttributeError.

Classes that override __getattribute__ get the kind K_HOOK for every name
in their attribute cache, so that every access goes to the hook.  The
compiler inlines the commonest cases (an attribute in the instance dict, a
set slot) and calls `inst_getattr` for the rest.
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any

from .calls import HOST_DESCRIPTORS, call, native_new
from .errors import EXC_REPR, NATIVE_EXC_ATTRS, exc_attr_value, exc_repr
from .lookup import (
    K_BASE_ANNOTATIONS,
    K_CLASS,
    K_CLASSM,
    K_DICT,
    K_EMU,
    K_FUNC,
    K_HDATA,
    K_HGET,
    K_HOOK,
    K_IDATA,
    K_IGET,
    K_ISET,
    K_MISSING,
    K_NATIVE,
    K_NODICT,
    K_PLAIN,
    K_PROP,
    K_SLOT,
    K_STATIC,
    OBJECT_METHODS,
    afill,
    has_class_attr,
    kind_of,
    lookup,
)
from .objects import MISSING, Class, Instance, Method, Super, invalidate
from .typechecks import allow_virtual_subclasses, type_name

if TYPE_CHECKING:
    from collections.abc import Callable

    from .lookup import Entry
    from .objects import Signal


# ---------------------------------------------------------------------------
# The descriptor protocol
# ---------------------------------------------------------------------------

def bind_value(v: Any, k: Signal, inst: Any, cls: Any) -> Any:
    """Apply the descriptor protocol to a class attribute value v of kind k
    found while looking up an attribute on inst (None for class access).

    Functions become bound methods, staticmethods unwrap, classmethods bind
    to the class, properties call their getter, and other descriptors have
    their __get__ called; an attribute of a host base class binds to the
    instance's native part.  Plain values are returned as they are.
    """
    if k is K_FUNC:
        return v if inst is None else Method(v, inst)
    if k is K_PLAIN or k is K_MISSING:
        return v
    if k is K_STATIC:
        return v.__func__
    if k is K_CLASSM:
        return Method(v.__func__, cls)
    if k is K_PROP:
        return v if inst is None else get_property(v, inst, cls)
    if k is K_IDATA or k is K_IGET:
        return call(inst_getattr(v, '__get__'), (inst, cls), None)
    if k is K_HDATA or k is K_HGET:
        return bind_host_descriptor(v, inst, cls)
    if k is K_EMU:
        return v if inst is None else Method(v, inst)
    if k is K_NATIVE and inst is not None:
        return bind_native_attr(v, inst)
    return v


def bind_native_attr(v: Any, inst: Instance) -> Any:
    """Attribute v of a host base class of inst's class, bound to inst's
    native part, or to inst itself when it has none (the base is then a
    stateless mixin such as collections.abc.Mapping)."""
    target: Any = inst if inst.native is None else inst.native
    get: Any = getattr(type(v), '__get__', None)
    if get is None:
        return v
    return get(v, target, target.cls if target is inst else type(target))


def bind_host_descriptor(v: Any, inst: Any, cls: Any) -> Any:
    """The __get__ of host descriptor v for inst (None for class access).
    An unbound method of a host base class stored in an interpreted class
    (`__getattr__ = dict.__getitem__`) binds to the instance's native part,
    the only object it can work on."""
    if inst is not None and inst.native is not None and type(v) in HOST_DESCRIPTORS:
        n: Any = inst.native
        return v.__get__(n, type(n))
    return v.__get__(inst, cls)


def get_property(prop: Any, inst: Any, cls: Any) -> Any:
    """Call the getter of property prop for inst (an instance of cls)."""
    if prop.fget is None:
        raise AttributeError(f"property of '{cls.__name__}' object has no getter")
    return call(prop.fget, (inst,), None)


# ---------------------------------------------------------------------------
# Reading attributes of instances
# ---------------------------------------------------------------------------

def inst_getattr(o: Instance, name: str) -> Any:
    """Read attribute `name` of instance o (the full `o.name`).

    The common kinds are handled here directly from the class's attribute
    cache; everything else goes through `resolve_inst_attr`, and a missing
    attribute (or an AttributeError raised by a property or descriptor)
    through `getattr_missing` (`getattr_after_error`): the __getattr__ hook.
    """
    cls: Class = o.cls
    e: Entry | None = cls.acache.get(name)
    if e is None:
        e = afill(cls, name)
    k: Signal = e[0]
    if k is K_MISSING:
        d: dict[str, Any] = o.d
        if name in d:
            return d[name]
        return getattr_missing(o, name)
    if k is K_FUNC:
        d = o.d
        if name in d:
            return d[name]
        return Method(e[1], o)
    if k is K_PLAIN:
        d = o.d
        if name in d:
            return d[name]
        return e[1]
    if k is K_HOOK:
        return getattr_hooked(o, name, e[1])
    try:
        r: Any = resolve_inst_attr(o, name, e)
    except AttributeError as err:
        return getattr_after_error(o, name, err)
    return getattr_missing(o, name) if r is MISSING else r


def resolve_inst_attr(o: Instance, name: str, e: Entry) -> Any:
    """Python's object.__getattribute__ for an Instance given the class
    lookup entry e.  Returns MISSING when the attribute does not exist.

    Data descriptors (properties, slots, objects defining __set__ or
    __delete__, and __class__) take precedence over the instance dict;
    everything else is shadowed by it.
    """
    k: Signal = e[0]
    v: Any = e[1]
    if k is K_PROP:
        if v.fget is None:
            raise AttributeError(f"property '{name}' of '{o.cls.__name__}' object has no getter")
        return call(v.fget, (o,), None)
    if k is K_SLOT:
        sv: dict[str, Any] | None = o.sv
        return sv[name] if sv is not None and name in sv else MISSING
    if k is K_IDATA or k is K_HDATA:
        return get_data_descriptor(o, k, v)
    if k is K_CLASS or k is K_DICT:
        # the data descriptors `object` provides: __class__ and __dict__
        return o.cls if k is K_CLASS else o.d
    d: dict[str, Any] = o.d
    if name in d:
        return d[name]
    if k is K_FUNC:
        return Method(v, o)
    if k is K_PLAIN:
        return v
    if k is K_MISSING or k is K_NODICT:
        return MISSING
    return get_nondata_attr(o, name, k, v)


def get_data_descriptor(o: Instance, k: Signal, v: Any) -> Any:
    """Call the __get__ of data descriptor v (an interpreted object if k is
    K_IDATA, a host one if K_HDATA) for instance o."""
    if k is K_IDATA:
        return call(inst_getattr(v, '__get__'), (o, o.cls), None)
    return v.__get__(o, o.cls)


def get_nondata_attr(o: Instance, name: str, k: Signal, v: Any) -> Any:
    """The value of class attribute v (of kind k) read through instance o,
    for the kinds `resolve_inst_attr` does not handle itself.

    An attribute of a host base class (K_NATIVE) is read from o's native
    part when it has one, so that e.g. an exception's `args` come from the
    real exception object.
    """
    if k is not K_NATIVE:
        return bind_value(v, k, o, o.cls)
    n: Any = o.native
    if n is not None:
        r: Any = getattr(n, name)
        if name in NATIVE_EXC_ATTRS:
            return exc_attr_value(name, r)
        return r
    if hasattr(type(v), '__get__'):
        return v.__get__(o, o.cls)
    return v


def getattr_hooked(o: Instance, name: str, hook: Any) -> Any:
    """Read an attribute of an instance whose class overrides
    __getattribute__; __getattr__ still runs if the hook raises
    AttributeError."""
    try:
        return call(hook, (o, name), None)
    except AttributeError:
        ge: Entry = lookup(o.cls, '__getattr__')
        if ge[0] is K_MISSING or ge[0] is K_NODICT:
            raise
        return call(bind_value(ge[1], ge[0], o, o.cls), (name,), None)


def getattr_after_error(o: Instance, name: str, err: AttributeError) -> Any:
    """Handle an AttributeError raised while reading `o.name` (by a property
    getter or a descriptor's __get__): as in Python, the class's
    __getattr__ supplies the value, and without one the error propagates."""
    e: Entry = lookup(o.cls, '__getattr__')
    if e[0] is K_MISSING or e[0] is K_NODICT:
        raise err
    return call(bind_value(e[1], e[0], o, o.cls), (name,), None)


def getattr_missing(o: Instance, name: str) -> Any:
    """Handle an attribute that normal lookup did not find: __dict__, an
    attribute that host code stored on the native part (such as the
    __notes__ of an exception, set by add_note), the class's __getattr__
    hook, or AttributeError."""
    if name == '__dict__' and not o.cls.dictless:
        return o.d
    if o.native is not None:
        nd: dict[str, Any] | None = getattr(o.native, '__dict__', None)
        if nd is not None and name in nd:
            return nd[name]
    e: Entry = lookup(o.cls, '__getattr__')
    if e[0] is not K_MISSING and e[0] is not K_NODICT:
        return call(bind_value(e[1], e[0], o, o.cls), (name,), None)
    raise no_attribute(o, name)


def no_attribute(o: Instance, name: str) -> AttributeError:
    """The error for reading a missing attribute of an instance."""
    return AttributeError(f"'{o.cls.__name__}' object has no attribute '{name}'", name=name, obj=o)


def generic_getattr(o: Instance, name: str) -> Any:
    """object.__getattribute__: the full lookup minus the __getattribute__
    and __getattr__ hooks."""
    r: Any = resolve_inst_attr(o, name, lookup(o.cls, name))
    if r is MISSING:
        if name == '__dict__' and not o.cls.dictless:
            return o.d
        raise no_attribute(o, name)
    return r


# ---------------------------------------------------------------------------
# Writing and deleting attributes of instances
# ---------------------------------------------------------------------------

def inst_setattr(o: Instance, name: str, value: Any) -> None:
    """Set attribute `name` of instance o (`o.name = value`), through the
    class's __setattr__ if it overrides it."""
    cls: Class = o.cls
    if cls.sethook is not None:
        call(cls.sethook, (o, name, value), None)
        return
    generic_setattr(o, name, value)


def generic_setattr(o: Instance, name: str, value: Any) -> None:
    """object.__setattr__: data descriptors found on the class handle the
    assignment, otherwise the value goes into the instance dict."""
    e: Entry = lookup(o.cls, name)
    k: Signal = e[0]
    if k is K_MISSING or k is K_FUNC or k is K_PLAIN or k is K_STATIC or k is K_CLASSM or k is K_EMU:
        if o.cls.dictless:
            raise read_only_attribute(o, name)
        o.d[name] = value
        return
    v: Any = e[1]
    if k is K_PROP:
        set_property(o, name, v, value)
    elif k is K_SLOT:
        if o.sv is None:
            o.sv = {}
        o.sv[name] = value
    elif k is K_IDATA or k is K_ISET or k is K_HDATA:
        set_descriptor(o, k, v, value)
    elif k is K_CLASS:
        set_class(o, value)
    elif k is K_DICT:
        set_dict(o, value)
    elif k is K_NODICT:
        raise AttributeError(f"'{o.cls.__name__}' object has no attribute '{name}' and no __dict__ for setting "
                             'new attributes', name=name, obj=o)
    else:
        set_other_attr(o, name, k, v, value)


def set_other_attr(o: Instance, name: str, k: Signal, v: Any, value: Any) -> None:
    """generic_setattr for the remaining kinds of class attribute v.  A data
    descriptor of a host base class (such as an exception's args or
    __cause__) sets the attribute on the native part; anything else stores
    the value in the instance dict."""
    if k is K_NATIVE and o.native is not None and hasattr(type(v), '__set__'):
        setattr(o.native, name, native_value(value))
    else:
        o.d[name] = value


def read_only_attribute(o: Instance, name: str) -> AttributeError:
    """The error for setting or deleting, through an instance of a
    __slots__ class (which has no __dict__), an attribute its class defines."""
    return AttributeError(f"'{o.cls.__name__}' object attribute '{name}' is read-only", name=name, obj=o)


def set_property(o: Instance, name: str, prop: Any, value: Any) -> None:
    """Assignment to o.name where the class attribute is property prop."""
    if prop.fset is None:
        raise AttributeError(f"property '{name}' of '{o.cls.__name__}' object has no setter")
    call(prop.fset, (o, value), None)


def set_descriptor(o: Instance, k: Signal, v: Any, value: Any) -> None:
    """Assignment to an attribute of o whose class attribute is v, a data
    descriptor of kind k (host or interpreted).  As in Python, an
    interpreted one defining only __get__ and __delete__ raises
    AttributeError('__set__')."""
    if k is K_HDATA:
        v.__set__(o, value)
        return
    if not has_class_attr(v.cls, '__set__'):
        raise AttributeError('__set__')
    call(inst_getattr(v, '__set__'), (o, value), None)


def native_value(value: Any) -> Any:
    """The host value to store in an attribute of a host object: the native
    part of an interpreted exception (the only kind of interpreted object
    that host exception attributes such as __cause__ accept), else value."""
    if type(value) is Instance and isinstance(value.native, BaseException):
        return value.native
    return value


def set_class(o: Instance, value: Any) -> None:
    """Assignment to o.__class__."""
    if type(value) is not Class:
        raise TypeError(f"__class__ must be set to a class, not '{type_name(value)}' object")
    o.cls = value


def set_dict(o: Instance, value: Any) -> None:
    """Assignment to o.__dict__: the new dict becomes o's attribute dict,
    which is also the host-level __dict__ of the Instance (see Instance)."""
    if not isinstance(value, dict):
        raise TypeError(f"__dict__ must be set to a dictionary, not a '{type_name(value)}'")
    o.__dict__ = value
    o.d = value


def inst_delattr(o: Instance, name: str) -> None:
    """Delete attribute `name` of instance o (`del o.name`), through the
    class's __delattr__ if it overrides it."""
    cls: Class = o.cls
    if cls.delhook is not None:
        call(cls.delhook, (o, name), None)
        return
    generic_delattr(o, name)


def generic_delattr(o: Instance, name: str) -> None:
    """object.__delattr__: data descriptors found on the class handle the
    deletion, otherwise the name is removed from the instance dict."""
    e: Entry = lookup(o.cls, name)
    k: Signal = e[0]
    v: Any = e[1]
    if k is K_PROP:
        if v.fdel is None:
            raise AttributeError(f"property '{name}' of '{o.cls.__name__}' object has no deleter")
        call(v.fdel, (o,), None)
        return
    if k is K_SLOT:
        if o.sv is not None and name in o.sv:
            del o.sv[name]
            return
        raise AttributeError(name)
    if k is K_IDATA or k is K_ISET:
        delete_descriptor(o, v)
        return
    if k is K_HDATA:
        v.__delete__(o)
        return
    if k is K_DICT:
        set_dict(o, {})
        return
    if name in o.d:
        del o.d[name]
        return
    raise no_attribute_to_delete(o, name, k)


def delete_descriptor(o: Instance, v: Instance) -> None:
    """Deletion of an attribute of o whose class attribute is v, an
    interpreted data descriptor; AttributeError('__delete__') if v does
    not define __delete__."""
    if not has_class_attr(v.cls, '__delete__'):
        raise AttributeError('__delete__')
    call(inst_getattr(v, '__delete__'), (o,), None)


def no_attribute_to_delete(o: Instance, name: str, k: Signal) -> AttributeError:
    """The error for deleting attribute `name` (of class lookup kind k) that
    instance o does not have."""
    if not o.cls.dictless:
        return no_attribute(o, name)
    if k is K_NODICT:
        return AttributeError(f"'{o.cls.__name__}' object has no attribute '{name}' and no __dict__ for setting "
                              'new attributes', name=name, obj=o)
    return read_only_attribute(o, name)


# ---------------------------------------------------------------------------
# Attributes of classes
# ---------------------------------------------------------------------------

def class_getattr(c: Class, name: str) -> Any:
    """Read attribute `name` of interpreted class c (`C.name`).

    Functions come back unbound, classmethods bind to c, and descriptors
    are called with no instance.  Names not in any namespace on the MRO
    fall back to the attributes every class has (`class_special`).
    """
    e: Entry = lookup(c, name)
    k: Signal = e[0]
    v: Any = e[1]
    if k is K_FUNC or k is K_PLAIN:
        return v
    if k is K_MISSING or k is K_NODICT:
        return class_special(c, name)
    if k is K_STATIC:
        return v.__func__
    if k is K_CLASSM:
        return Method(v.__func__, c)
    if k is K_PROP or k is K_SLOT or k is K_EMU:
        if name == '__name__' or name == '__qualname__':
            # the class's own name wins over a property or slot for its
            # instances, as with CPython's type.__name__
            return class_special(c, name)
        return v
    if k is K_NATIVE:
        return getattr(e[2], name)
    if k is K_CLASS:
        return type
    if k is K_DICT or k is K_BASE_ANNOTATIONS:
        return class_special(c, name)
    return bind_value(v, k, None, c)


CLASS_SPECIALS: dict[str, Callable[[Class], Any]] = {
    '__name__': lambda c: c.__name__,
    '__qualname__': lambda c: c.__qualname__,
    '__module__': lambda c: c.__module__,
    '__dict__': lambda c: types.MappingProxyType(c.ns),
    '__mro__': lambda c: tuple(c.mro),
    '__bases__': lambda c: c.__bases__,
    '__base__': lambda c: c.__bases__[0] if c.__bases__ else None,
    '__class__': lambda c: type,
    '__doc__': lambda c: None,
    '__annotations__': lambda c: new_class_annotations(c),
    '__type_params__': lambda c: (),
    'register': lambda c: abc_register_method(c),
    'mro': lambda c: lambda: list(c.mro),
    '__subclasses__': lambda c: lambda: list(c.subclasses),
}
"""The attributes that every class has without storing them in its
namespace (CPython finds them on `type`), each computed from the class."""


def class_getitem(c: Class, item: Any) -> Any:
    """`C[item]` for interpreted class c: c.__class_getitem__(item)."""
    e: Entry = lookup(c, '__class_getitem__')
    k: Signal = e[0]
    v: Any = e[1]
    if k is K_MISSING or k is K_NODICT:
        raise TypeError(f"type '{c.__name__}' is not subscriptable")
    if k is K_NATIVE:
        return host_class_getitem(c, v, item)
    return call(class_getattr(c, '__class_getitem__'), (item,), None)


def host_class_getitem(c: Class, v: Any, item: Any) -> Any:
    """`C[item]` where the __class_getitem__ v of interpreted class c comes
    from a host base class: a Python classmethod is bound to c rather than
    the base; the builtin ones (list's, typing.Generic's), which only accept
    host types, are replaced by the generic alias they would make."""
    if type(v) is classmethod:
        get: Any = v.__get__
        return get(None, c)(item)
    alias: Any = types.GenericAlias
    return alias(c, item)


def new_class_annotations(c: Class) -> dict[str, Any]:
    """C.__annotations__ for a class without annotations of its own: a new
    empty dict, stored in the namespace (as Python 3.13 does)."""
    d: dict[str, Any] = {}
    c.ns['__annotations__'] = d
    invalidate(c)
    return d


def abc_register_method(c: Class) -> Callable[[Any], Any]:
    """C.register for an abstract base class C (the method abc.ABCMeta
    gives its classes): register a virtual subclass, returning it."""
    if c.abc_registry is None:
        raise AttributeError(f"type object '{c.__name__}' has no attribute 'register'", name='register', obj=c)
    registry: list[Any] = c.abc_registry

    def register(subclass: Any) -> Any:
        if type(subclass) is not Class and not isinstance(subclass, type):
            raise TypeError('Can only register classes')
        if subclass not in registry:
            registry.append(subclass)
            allow_virtual_subclasses()
        return subclass
    return register


def class_special(c: Class, name: str) -> Any:
    """Read one of the attributes every class has (see CLASS_SPECIALS)."""
    getter: Callable[[Class], Any] | None = CLASS_SPECIALS.get(name)
    if getter is None:
        raise AttributeError(f"type object '{c.__name__}' has no attribute '{name}'", name=name, obj=c)
    return getter(c)


def class_setattr(c: Class, name: str, value: Any) -> None:
    """Set attribute `name` of interpreted class c, invalidating the
    attribute caches of c and its subclasses."""
    if name == '__name__':
        c.__name__ = value
        return
    if name == '__qualname__':
        c.__qualname__ = value
        return
    if name == '__module__':
        c.__module__ = value
    c.ns[name] = value
    invalidate(c)


def class_delattr(c: Class, name: str) -> None:
    """Delete attribute `name` from the namespace of interpreted class c."""
    if name not in c.ns:
        raise AttributeError(f"type object '{c.__name__}' has no attribute '{name}'")
    del c.ns[name]
    invalidate(c)


# ---------------------------------------------------------------------------
# super()
# ---------------------------------------------------------------------------

def super_getattr(s: Super, name: str) -> Any:
    """Read attribute `name` of super object s: search the MRO of the
    object's type, starting after s.thisclass, and bind what is found to
    the object."""
    objtype: Any = s.objtype
    # (an unbound super object has no objtype, None, and no MRO)
    mro: list[Any] = objtype.mro if type(objtype) is Class else list(getattr(objtype, '__mro__', ()))
    i: int = 0
    n: int = len(mro)
    while i < n and mro[i] is not s.thisclass:
        i += 1
    obj: Any = s.obj
    inst: Instance | None = obj if type(obj) is Instance else None
    for k in mro[i + 1:]:
        if type(k) is Class:
            ns: dict[str, Any] = k.ns
            if name in ns:
                v: Any = ns[name]
                kind: Signal = kind_of(v)
                if kind is K_FUNC and name == '__new__':
                    return v
                return bind_value(v, kind, inst, objtype)
        elif k is object:
            return super_object_attr(obj, inst, objtype, name, s)
        elif name in k.__dict__:
            if inst is None and type(objtype) is not Class and name != '__new__':
                return super_bind_host(k.__dict__[name], obj, objtype)
            return super_host_attr(k, inst, name)
    return super_own_attr(s, name)


def super_bind_host(v: Any, obj: Any, objtype: Any) -> Any:
    """The attribute v of a host base class found by super() for a host
    object, as in the methods of a class made by a host metaclass (an enum,
    a NamedTuple): bound the way CPython's super binds it, to the object, or
    to nothing when the object is the class itself."""
    get: Any = getattr(type(v), '__get__', None)
    if get is None:
        return v
    return get(v, None if obj is objtype else obj, objtype)


def super_object_attr(obj: Any, inst: Instance | None, objtype: Any, name: str, s: Super) -> Any:
    """super() reaching `object`: one of the emulated object methods, or
    __class__, or else an attribute of the super object s itself."""
    f: Callable[..., Any] | None = OBJECT_METHODS.get(name)
    if f is not None:
        if name == '__new__':
            return f
        if name == '__init_subclass__' or name == '__subclasshook__':
            return Method(f, objtype)
        return f if inst is None else Method(f, inst)
    if name == '__class__':
        return type(obj) if inst is None else inst.cls
    return super_own_attr(s, name)


def super_own_attr(s: Super, name: str) -> Any:
    """An attribute of super object s itself (__thisclass__, __self__ and
    __self_class__), for a name the search of the MRO did not find."""
    if name == '__thisclass__':
        return s.thisclass
    if name == '__self__':
        return s.obj
    if name == '__self_class__':
        return s.objtype
    raise no_super_attribute(name)


def super_host_attr(k: type, inst: Instance | None, name: str) -> Any:
    """super() reaching host class k, which defines `name`: k's attribute
    bound to the instance's native part, or to the instance itself when it
    has none (k is then a stateless mixin such as collections.abc.Mapping).
    It is k's own attribute that is bound, not what the native's class has
    under that name (which may forward back to the interpreted method)."""
    if name == '__new__':
        return native_new
    if inst is None:
        return getattr(k, name)
    if inst.native is not None and k.__dict__[name] is EXC_REPR:
        return bound_exc_repr(inst)
    return bind_native_attr(k.__dict__[name], inst)


def bound_exc_repr(inst: Instance) -> Callable[[], str]:
    """super().__repr__ reaching BaseException.__repr__ for interpreted
    exception inst: it names inst's class, not the host base class."""
    def exc_repr_method() -> str:
        return exc_repr(inst.cls.__name__, inst.native.args)
    return exc_repr_method


def no_super_attribute(name: str) -> AttributeError:
    """The error for an attribute that super() did not find."""
    return AttributeError(f"'super' object has no attribute '{name}'", name=name)


# ---------------------------------------------------------------------------
# Host code reading __doc__ and __module__ of interpreted objects
# ---------------------------------------------------------------------------
#
# The host classes Instance and Class have a docstring and a module of their
# own, which host code reading these attributes (property(), functools.wraps,
# inspect.getdoc, ...) would otherwise find before Instance.__getattr__ or
# Class.__getattr__ forwards the read to the interpreted object.  They are
# replaced by non-data descriptors that read the interpreted attribute; host
# code setting the attribute on an instance still stores it in its dict.

class InstanceDoc:
    """Instance.__doc__: the __doc__ of the interpreted object."""

    def __get__(self, inst: Any, owner: Any = None) -> Any:
        if inst is None:
            return None
        return inst_getattr(inst, '__doc__')


class InstanceModule(str):
    """Instance.__module__: the __module__ of the interpreted object.  It is
    a str, the host module of Instance, because the __module__ of a host
    class must be one."""

    def __get__(self, inst: Any, owner: Any = None) -> Any:
        if inst is None:
            return self
        return inst_getattr(inst, '__module__')


class ClassDoc:
    """Class.__doc__: the docstring of the interpreted class."""

    def __get__(self, c: Any, owner: Any = None) -> Any:
        if c is None:
            return None
        return class_getattr(c, '__doc__')


def host_dir(o: Any) -> list[Any]:
    """Instance.__dir__ and Class.__dir__: host code's dir() of an
    interpreted object or class (unittest's loader, inspect, ...) lists what
    dir() in interpreted code does, not the host object's internals."""
    from .builtin_functions import b_dir
    return b_dir(o)


class ShadowAttr:
    """An attribute of a shadow class (see calls.shadow_class), standing
    for attribute `name` of interpreted class `cls`.  Read on a native part,
    it is the attribute of the interpreted object the native belongs to
    (so a method is bound to that object); read on the shadow class, it is
    the interpreted class's.  As a non-data descriptor, it gives way to
    attributes in the instance dict the native shares with the object."""

    __slots__ = ('cls', 'name')

    def __init__(self, cls: Class, name: str) -> None:
        self.cls: Class = cls
        self.name: str = name

    def __get__(self, native: Any, owner: Any = None) -> Any:
        if native is None:
            return class_getattr(self.cls, self.name)
        return inst_getattr(native._boros_inst, self.name)


def install_host_descriptors() -> None:
    """Replace the host attributes __doc__ and __module__ of Instance and
    Class by the descriptors above, and give them a host-level __dir__."""
    descriptors: list[tuple[type, str, Any]] = [
        (Instance, '__doc__', InstanceDoc()),
        (Instance, '__module__', InstanceModule(Instance.__module__)),
        (Class, '__doc__', ClassDoc()),
        (Instance, '__dir__', host_dir),
        (Class, '__dir__', host_dir),
    ]
    for host_class, name, descriptor in descriptors:
        setattr(host_class, name, descriptor)


install_host_descriptors()


# ---------------------------------------------------------------------------
# getattr/setattr/delattr on any object
# ---------------------------------------------------------------------------

def getattr_any(o: Any, name: str) -> Any:
    """Read attribute `name` of any object, interpreted or host."""
    t: type = type(o)
    if t is Instance:
        return inst_getattr(o, name)
    if t is Class:
        return class_getattr(o, name)
    if t is Super:
        return super_getattr(o, name)
    if o is object:
        f: Callable[..., Any] | None = OBJECT_METHODS.get(name)
        if f is not None:
            return f
    return getattr(o, name)


def setattr_any(o: Any, name: str, value: Any) -> None:
    """Set attribute `name` of any object, interpreted or host."""
    t: type = type(o)
    if t is Instance:
        inst_setattr(o, name, value)
    elif t is Class:
        class_setattr(o, name, value)
    else:
        try:
            setattr(o, name, value)
        except TypeError:
            # e.g. host_exception.__context__ = interpreted exception
            n: Any = native_value(value)
            if n is value:
                raise
            setattr(o, name, n)


def delattr_any(o: Any, name: str) -> None:
    """Delete attribute `name` of any object, interpreted or host."""
    t: type = type(o)
    if t is Instance:
        inst_delattr(o, name)
    elif t is Class:
        class_delattr(o, name)
    else:
        delattr(o, name)
