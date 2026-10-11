"""Emulations of the methods of the host `object` type for interpreted instances.

Every interpreted class ends its method resolution order with the host
`object`.  When an attribute lookup reaches it, lookup.find_attr() takes the
method from OBJECT_METHODS (filled in at the end of this module) rather than
from `object` itself, because the real object.__init__, object.__repr__, ...
would see the host Instance wrapper instead of the interpreted object.  So
`super().__init__()`, the default repr `<__main__.C object at 0x...>`, the
default `==` and the generic attribute access all come from here.

The functions can also be reached with a host object as `self` (for example
`C.__repr__(5)` for an interpreted class C), in which case they defer to the
real `object` method.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .attributes import generic_delattr, generic_getattr, generic_setattr
from .calls import make_native
from .lookup import K_EMU, OBJECT_METHODS, abstract_class_error, lookup
from .objects import MISSING, Class, Instance
from .protocols import call_special
from .typechecks import type_name

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import NotImplementedType


def obj_init(self: Any, *args: Any, **kw: Any) -> None:
    """object.__init__: does nothing.  Like CPython, it accepts arguments only
    when the class overrides __new__ but not __init__ (so the arguments were
    meant for __new__)."""
    if args or kw:
        if type(self) is Instance:
            c: Class = self.cls
            if lookup(c, '__init__')[0] is not K_EMU:
                raise TypeError('object.__init__() takes exactly one argument (the instance to initialize)')
            if lookup(c, '__new__')[0] is K_EMU:
                raise TypeError(f'{c.__name__}() takes no arguments')
        else:
            object.__init__(self, *args, **kw)


def obj_new(cls: Any, *args: Any, **kw: Any) -> Any:
    """object.__new__: a new, empty Instance of interpreted class cls (with
    its host object if cls derives from a host type such as Exception).

    Like CPython, it accepts arguments only when cls overrides __init__ but
    not __new__ (so the arguments are meant for __init__).
    """
    if type(cls) is not Class:
        return object.__new__(cls, *args, **kw)
    if (args or kw) and (lookup(cls, '__new__')[0] is not K_EMU or lookup(cls, '__init__')[0] is K_EMU):
        if lookup(cls, '__new__')[0] is not K_EMU:
            raise TypeError('object.__new__() takes exactly one argument (the type to instantiate)')
        raise TypeError(f'{cls.__name__}() takes no arguments')
    if cls.ns.get('__abstractmethods__'):
        raise abstract_class_error(cls)
    inst: Instance = Instance(cls)
    if cls.native is not None:
        make_native(inst, cls.native, args, kw or None)
    return inst


def obj_repr(self: Any) -> str:
    """object.__repr__: `<module.QualName object at 0x...>`."""
    if type(self) is not Instance:
        return object.__repr__(self)
    c: Class = self.cls
    return f'<{c.__module__}.{c.__qualname__} object at 0x{id(self):x}>'


def obj_str(self: Any) -> Any:
    """object.__str__: the repr.  For an interpreted instance, the result of
    its __repr__ unchecked: str() itself checks it ("__str__ returned
    non-string")."""
    if type(self) is Instance:
        return call_special(self, '__repr__', ())
    return repr(self)


def obj_eq(self: Any, other: Any) -> bool | NotImplementedType:
    """object.__eq__: identity; NotImplemented lets the other operand decide."""
    if self is other:
        return True
    return NotImplemented


def obj_ne(self: Any, other: Any) -> bool | NotImplementedType:
    """object.__ne__: the negation of __eq__, unless that is NotImplemented."""
    if type(self) is Instance:
        r: Any = call_special(self, '__eq__', (other,))
        if r is MISSING or r is NotImplemented:
            return NotImplemented
        return not r
    return object.__ne__(self, other)


def obj_hash(self: Any) -> int:
    """object.__hash__: based on identity."""
    return object.__hash__(self)


def obj_format(self: Any, spec: str) -> str:
    """object.__format__: str(self), and only for an empty format spec."""
    if spec:
        raise TypeError(f'unsupported format string passed to {type_name(self)}.__format__')
    return str(self)


def obj_getattribute(self: Any, name: str) -> Any:
    """object.__getattribute__: the full attribute lookup without the
    __getattribute__ and __getattr__ hooks."""
    if type(self) is Instance:
        return generic_getattr(self, name)
    return object.__getattribute__(self, name)


def obj_setattr(self: Any, name: str, value: Any) -> None:
    """object.__setattr__: set an attribute, bypassing a __setattr__ hook."""
    if type(self) is Instance:
        generic_setattr(self, name, value)
    else:
        object.__setattr__(self, name, value)


def obj_delattr(self: Any, name: str) -> None:
    """object.__delattr__: delete an attribute, bypassing a __delattr__ hook."""
    if type(self) is Instance:
        generic_delattr(self, name)
    else:
        object.__delattr__(self, name)


def obj_dir(self: Any) -> Any:
    """object.__dir__: the names dir() lists."""
    from .builtin_functions import b_dir
    return b_dir(self)


def obj_init_subclass(cls: Any, **kw: Any) -> None:
    """object.__init_subclass__: called for each new subclass; takes no
    class keyword arguments."""
    if kw:
        raise TypeError(f'{cls.__name__}.__init_subclass__() takes no keyword arguments')


def obj_subclasshook(cls: Any, *args: Any) -> NotImplementedType:
    """object.__subclasshook__: leaves issubclass() to the normal rules."""
    return NotImplemented


def obj_reduce_ex(self: Instance, protocol: int) -> tuple[Callable[[Class, Any], Instance], tuple[Class, Any],
                                                          dict[str, Any]]:
    """object.__reduce_ex__ for pickling and copying: rebuild the instance
    with copy_instance_reconstruct() and restore its state.  (Not currently
    registered in OBJECT_METHODS.)"""
    return (copy_instance_reconstruct, (self.cls, self.native), {'d': self.d, 'sv': self.sv})


def obj_sizeof(self: Any) -> int:
    """object.__sizeof__."""
    return object.__sizeof__(self)


def obj_getstate(self: Any) -> Any:
    """object.__getstate__: the instance dict, or None when it is empty."""
    if type(self) is Instance:
        return self.d or None
    return object.__getstate__(self)


def copy_instance_reconstruct(cls: Class, native: Any) -> Instance:
    """Recreate an instance of cls around host object `native` (see obj_reduce_ex)."""
    inst: Instance = Instance(cls)
    inst.native = native
    return inst


OBJECT_METHODS.update({
    '__init__': obj_init, '__new__': obj_new, '__repr__': obj_repr, '__str__': obj_str,
    '__eq__': obj_eq, '__ne__': obj_ne, '__hash__': obj_hash, '__format__': obj_format,
    '__getattribute__': obj_getattribute, '__setattr__': obj_setattr, '__delattr__': obj_delattr,
    '__dir__': obj_dir, '__init_subclass__': obj_init_subclass, '__subclasshook__': obj_subclasshook,
    '__sizeof__': obj_sizeof, '__getstate__': obj_getstate,
})
