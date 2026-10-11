"""Creating classes: the class statement and type(name, bases, ns).

A class statement first runs its body on a fresh namespace dict, then calls
`build_class`, which does what CPython's type.__new__ does for an ordinary
class: resolve the bases, apply the implicit decorators (__new__ is a
staticmethod, __init_subclass__ and __class_getitem__ are classmethods),
create the Class object (which computes the MRO), call __set_name__ on the
attributes that define it, and finally call __init_subclass__ of the
parent class.

A class whose metaclass is a host metaclass other than `type`, such as
enum.EnumType or typing.NamedTupleMeta, is made by that metaclass instead:
it is a host class (holding interpreted functions), and its body runs in
the namespace the metaclass's __prepare__ returns.  abc.ABCMeta is the
exception: abstract base classes are interpreted classes that emulate it
(see setup_abc).
"""

from __future__ import annotations

from abc import ABCMeta
from typing import TYPE_CHECKING, Any

from .attributes import getattr_any, super_getattr
from .calls import call, type_of
from .lookup import K_MISSING, K_NODICT, has_special, lookup
from .objects import Class, Function, Instance, Super, invalidate
from .protocols import call_special
from .typechecks import allow_virtual_subclasses, metaclass_of, type_name

if TYPE_CHECKING:
    from _collections_abc import dict_items, dict_keys, dict_values
    from collections.abc import Iterator

    from ..core_types import Frame, Kwargs


def build_class(name: str, bases: list[Any], ns: Frame, kw: Kwargs) -> Any:
    """Create interpreted class `name` from its bases, the namespace its body
    produced, and the keyword arguments of the class statement (passed on
    to __init_subclass__), or a host class if a host metaclass makes it.
    Interpreted metaclasses are not supported."""
    meta: Any = kw.pop('metaclass', None) if kw else None
    if meta is not None and meta is not type and type(meta) is Class:
        raise TypeError('boros does not support interpreted metaclasses')
    resolved: list[Any] = resolve_bases(bases)
    hmeta: Any = host_metaclass(meta, resolved) if meta is not None or has_host_base(bases) else None
    if hmeta is not None:
        return make_host_class(hmeta, name, bases, resolved, ns, kw)
    prepare_namespace(ns)
    cls: Class = Class(name, tuple(resolved), ns)
    if is_abc(meta, cls.__bases__):
        setup_abc(cls)
    set_names(cls, ns)
    init_sub: Any = super_getattr(Super(cls, cls), '__init_subclass__')
    call(init_sub, (), kw or None)
    return cls


class ClassNamespace(dict):
    """The namespace of a class body that calls locals() (or vars(), dir(),
    exec(), eval()), which returns it, so that writes to it define class
    attributes.  It hides the interpreter's bookkeeping keys ('.up', '.cls')
    from the program."""

    def visible(self) -> dict[Any, Any]:
        """A copy of the namespace without the bookkeeping keys."""
        return {k: v for k, v in dict.items(self) if type(k) is not str or k[:1] != '.'}

    def __iter__(self) -> Iterator[Any]:
        return iter(self.visible())

    def keys(self) -> dict_keys[Any, Any]:
        return self.visible().keys()

    def values(self) -> dict_values[Any, Any]:
        return self.visible().values()

    def items(self) -> dict_items[Any, Any]:
        return self.visible().items()

    def __len__(self) -> int:
        return len(self.visible())

    def copy(self) -> dict[Any, Any]:
        return self.visible()

    def __repr__(self) -> str:
        return repr(self.visible())


def class_namespace(name: str, bases: list[Any], kw: dict[str, Any], ns: Frame) -> Frame:
    """The namespace a class statement runs its body in: ns itself, or for a
    class that a host metaclass makes, the mapping returned by the
    metaclass's __prepare__, holding the entries of ns.  The bookkeeping
    entries ('.up', '.cls') bypass the mapping's own __setitem__."""
    if 'metaclass' not in kw and not has_host_base(bases):
        return ns
    resolved: list[Any] = resolve_bases(bases)
    hmeta: Any = host_metaclass(kw.get('metaclass'), resolved)
    if hmeta is None:
        return ns
    prepare: Any = getattr(hmeta, '__prepare__', None)
    hns: Any = {} if prepare is None else prepare(name, tuple(resolved), **class_keywords(kw))
    for k, v in ns.items():
        if k[0] == '.':
            dict.__setitem__(hns, k, v)
        else:
            hns[k] = v
    return hns


def has_host_base(bases: list[Any]) -> bool:
    """Whether a class statement names a base that is not an interpreted
    class (only then can a host metaclass be involved)."""
    for b in bases:
        if type(b) is not Class:
            return True
    return False


def class_keywords(kw: dict[str, Any]) -> dict[str, Any]:
    """The keyword arguments of a class statement other than metaclass=."""
    out: dict[str, Any] = dict(kw)
    out.pop('metaclass', None)
    return out


def host_metaclass(meta: Any, bases: list[Any]) -> Any:
    """The host metaclass that must make a new class, or None for an
    interpreted class.  As in CPython the metaclass is the most derived of
    the explicit one and those of the bases; it makes a host class unless it
    is `type` or (emulated) abc.ABCMeta, or is interpreted (an error).  An
    explicit metaclass that is not a class is simply called."""
    if type(meta) is Class:
        return None
    if meta is not None and not isinstance(meta, type):
        return meta
    winner: Any = type if meta is None else meta
    for b in bases:
        mt: Any = metaclass_of(b) if type(b) is Class else type(b)
        if issubclass(mt, winner):
            winner = mt
        elif not issubclass(winner, mt):
            raise TypeError('metaclass conflict: the metaclass of a derived class must be a (non-strict) '
                            'subclass of the metaclasses of all its bases')
    if winner is type or issubclass(winner, ABCMeta):
        return None
    return winner


def make_host_class(meta: Any, name: str, bases: list[Any], resolved: list[Any], ns: Any, kw: Kwargs) -> Any:
    """Have host metaclass `meta` make class `name` from the namespace the
    class body filled in.  Its methods stay interpreted functions, which
    the host binds through Function.__get__."""
    for b in resolved:
        if type(b) is Class and isinstance(meta, type):
            raise TypeError(f'boros cannot combine the interpreted class {b.__name__} with the host metaclass '
                            f'{meta.__name__}')
    if resolved != bases and bases:
        # some bases were replaced through __mro_entries__ (e.g. typing.NamedTuple)
        ns['__orig_bases__'] = tuple(bases)
    hbases: tuple[Any, ...] = tuple(resolved) if bases else ()
    if kw:
        return meta(name, hbases, ns, **kw)
    return meta(name, hbases, ns)


def resolve_bases(bases: list[Any]) -> list[Any]:
    """The real bases of a class: a base that is not a class may stand for
    others through __mro_entries__ (e.g. typing.Generic[T]), and a class
    with no bases derives from object."""
    resolved: list[Any] = []
    for b in bases:
        if type(b) is not Class and not isinstance(b, type):
            entries: Any = getattr(b, '__mro_entries__', None)
            if entries is None:
                raise TypeError('bases must be types')
            resolved.extend(entries(tuple(bases)))
        else:
            resolved.append(b)
    if not resolved:
        resolved.append(object)
    return resolved


def prepare_namespace(ns: Frame) -> None:
    """Apply the implicit rules of class creation to namespace ns: __new__
    is a staticmethod, __init_subclass__ and __class_getitem__ are
    classmethods, defining __eq__ without __hash__ makes instances
    unhashable, and __doc__ defaults to None."""
    if '__new__' in ns and type(ns['__new__']) is Function:
        ns['__new__'] = staticmethod(ns['__new__'])
    for special in ('__init_subclass__', '__class_getitem__'):
        if special in ns and type(ns[special]) is Function:
            ns[special] = classmethod(ns[special])
    if '__eq__' in ns and '__hash__' not in ns:
        ns['__hash__'] = None
    if '__doc__' not in ns:
        ns['__doc__'] = None


def is_abc(meta: Any, bases: tuple[Any, ...]) -> bool:
    """Whether abc.ABCMeta makes a new interpreted class: it is the explicit
    metaclass, or a base class is an abstract base class."""
    if meta is not None and issubclass(meta, ABCMeta):
        return True
    for b in bases:
        if type(b) is Class:
            if b.abc_registry is not None:
                return True
        elif b is not object and isinstance(b, ABCMeta):
            return True
    return False


def setup_abc(cls: Class) -> None:
    """What abc.ABCMeta.__new__ does: store in cls.__abstractmethods__ the
    names of its abstract methods (its own, and the inherited ones it does
    not implement), and start its registry of virtual subclasses.  A class
    with abstract methods cannot be instantiated (see lookup.object_entry)."""
    names: set[str] = set()
    for k, v in cls.ns.items():
        if is_abstract(v):
            names.add(k)
    for b in cls.__bases__:
        for name in base_abstracts(b):
            e: Any = lookup(cls, name)
            if e[0] is K_MISSING or e[0] is K_NODICT or is_abstract(e[1]):
                names.add(name)
    cls.ns['__abstractmethods__'] = frozenset(names)
    cls.abc_registry = []
    if '__subclasshook__' in cls.ns:
        allow_virtual_subclasses()
    invalidate(cls)


def base_abstracts(b: Any) -> Any:
    """The names of the abstract methods of base class b."""
    if type(b) is Class:
        return b.ns.get('__abstractmethods__', ())
    return getattr(b, '__abstractmethods__', ())


def is_abstract(v: Any) -> bool:
    """Whether class attribute v is abstract: its __isabstractmethod__ is true."""
    try:
        return bool(getattr_any(v, '__isabstractmethod__'))
    except AttributeError:
        return False


def set_names(cls: Class, ns: Frame) -> None:
    """Call __set_name__(cls, name) on every attribute in the namespace of
    the new class cls that defines it (descriptors that want to know their
    name)."""
    for k in list(ns):
        v: Any = ns[k]
        if type(v) is Instance:
            if has_special(v, '__set_name__'):
                call_special(v, '__set_name__', (cls, k))
        elif type(v) is not Function and hasattr(type(v), '__set_name__'):
            v.__set_name__(cls, k)


def b_type(*args: Any, **kw: Any) -> Any:
    """The `type` builtin: type(x) gives the class of x, and
    type(name, bases, ns) creates a class."""
    if len(args) == 1 and not kw:
        return type_of(args[0])
    if len(args) == 3:
        check_type_args(args)
        name: str = args[0]
        ns: Frame = dict(args[2])
        ns.setdefault('__qualname__', name)
        ns.setdefault('__module__', '__main__')
        return build_class(name, list(args[1]), ns, kw)
    raise TypeError('type() takes 1 or 3 arguments')


def check_type_args(args: tuple[Any, ...]) -> None:
    """Check the argument types of type(name, bases, ns), with CPython's messages."""
    wanted: tuple[type, ...] = (str, tuple, dict)
    for i, want in enumerate(wanted):
        if not isinstance(args[i], want):
            raise TypeError(f'type.__new__() argument {i + 1} must be {want.__name__}, not {type_name(args[i])}')
