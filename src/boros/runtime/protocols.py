"""Special methods: making host operations work on interpreted objects.

Every object created from an interpreted class is a host `Instance`.  The
compiled code evaluates `a + b`, `len(x)`, `x[k]`, `str(x)`, `if x:` ... with
the host's own operators, and the host looks special methods up on the *host*
type of the operand -- always `Instance`, never the interpreted class.  So
this module installs on Instance one host method per special method (see
INSTANCE_METHODS at the end of the forwarding section), and each of them
forwards to the method the interpreted class defines, via call_special().
That keeps the compiled closures simple and fast: they never check whether an
operand is an interpreted object.

The forwarders also reproduce the rules the host applies when it looks for an
operator's implementation, since from the host's point of view both operands
of `a + b` have the same type, Instance:

- reflected operands: `a + b` falls back to `b.__radd__(a)`, and the right
  operand goes first when its class is a subclass that overrides the
  reflected method;
- in-place operators fall back to the binary operator;
- `==` and `!=` fall back to identity;
- truth testing falls back to __len__, iteration and `in` to __getitem__;
- a host sequence on the left of `+` or `*` falls back to concatenation or
  repetition, and a host value to its own method applied to the native
  part of an instance of a host type's subclass (`[0] + MyList([1])`);
- the TypeError messages Python uses when a method is missing.

The last sections have the helpers the compiler uses for `with`, `async
with`, `await` and `async for`, and the forwarders that let host code
(asyncio, aiter(), contextlib) await interpreted objects.
"""

from __future__ import annotations

import math
import operator
import sys
import types
from typing import TYPE_CHECKING, Any

from .attributes import bind_value, inst_getattr
from .calls import call, invoke
from .errors import EXC_REPR, INST_KEY, exc_repr, exc_triple, exc_value
from .lookup import K_EMU, K_FUNC, K_MISSING, K_NATIVE, K_NODICT, K_PLAIN, has_special, lookup
from .objects import MISSING, Instance
from .typechecks import type_name

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ..core_types import Args
    from .objects import Class, Signal

    Entry = tuple[Signal, Any, Any]
    """A class attribute lookup result (kind, value, defining class); the same as lookup.Entry."""

    UnaryMethod = Callable[[Instance], Any]
    """A host special method of Instance taking no arguments, such as __neg__."""

    BinaryMethod = Callable[[Instance, Any], Any]
    """A host special method of Instance taking one operand, such as __add__."""


# ---------------------------------------------------------------------------
# Calling a special method of an interpreted object
# ---------------------------------------------------------------------------

def call_special(o: Instance, name: str, args: Args) -> Any:
    """Call the special method `name` of instance o with `args`, returning
    MISSING if its class does not define it.

    As in Python, the method is looked up on the class only (an attribute in
    the instance dict does not count).  How it is called depends on the kind
    of class attribute that lookup() found:

    - an interpreted function: invoke it with o as first argument (the fast,
      common case);
    - one of the emulated `object` methods of object_methods.py: call it;
    - a method of a host base class (e.g. list or Exception): call it on the
      host object `o.native` standing in for that base (operands that are
      themselves such instances are passed as their native parts too, see
      native_operands);
    - anything else (staticmethod, classmethod, a callable instance, ...):
      apply the descriptor protocol with bind_value() and call the result.
      An attribute set to None (like `__bool__ = None`) is called too, which
      raises "'NoneType' object is not callable" as in Python; the methods
      whose None means something else (__hash__, __iter__, ...) check first.
    """
    e: Entry = lookup(o.cls, name)
    k: Signal = e[0]
    if k is K_FUNC:
        return invoke(e[1], (o,) + args, None)
    if k is K_MISSING or k is K_NODICT:
        return MISSING
    if k is K_EMU:
        return e[1](o, *args)
    if k is K_NATIVE:
        n: Any = o.native
        if n is None:
            return call_mixin_special(o, e[1], args)
        if e[1] is EXC_REPR:
            return exc_repr(o.cls.__name__, n.args)
        m: Any = getattr(n, name, None)
        if m is None:
            return MISSING
        if args and type(args[0]) is Instance and name in NATIVE_OPERAND_METHODS:
            return m(*native_operands(args))
        return m(*args)
    return call(bind_value(e[1], k, o, o.cls), args, None)


def call_mixin_special(o: Instance, v: Any, args: Args) -> Any:
    """Call special method v, found in a host base class of o's class, for
    an instance with no native part: v comes from a stateless mixin (e.g.
    Mapping.__contains__, Set.__and__), so it runs on o itself.  MISSING
    if v is not a method (such as `__hash__ = None`)."""
    get: Any = getattr(type(v), '__get__', None)
    if get is None:
        return MISSING
    return get(v, o, o.cls)(*args)


def native_operands(args: Args) -> Args:
    """The operands of a host base class's operator method (int.__add__,
    str.__eq__, list.__iadd__, ...), with each interpreted instance of a
    class deriving from a host type replaced by its native part: the host
    method only understands host values, while Python's own accepts any
    instance of a subclass."""
    out: list[Any] = []
    for a in args:
        if type(a) is Instance and a.native is not None:
            a = a.native
        out.append(a)
    return tuple(out)


def special_is_none(o: Instance, name: str) -> bool:
    """Whether the class of o sets special method `name` to None, which
    blocks it (for example `__iter__ = None`)."""
    e: Entry = lookup(o.cls, name)
    return e[0] is K_PLAIN and e[1] is None


# ---------------------------------------------------------------------------
# Binary operators: a + b, a - b, ..., divmod(a, b), and their reflected and
# in-place forms
# ---------------------------------------------------------------------------

BINARY_OPERATORS: list[tuple[str, str, str | None]] = [
    ('add', '+', '+='), ('sub', '-', '-='), ('mul', '*', '*='), ('truediv', '/', '/='),
    ('floordiv', '//', '//='), ('mod', '%', '%='), ('pow', '** or pow()', '**='), ('lshift', '<<', '<<='),
    ('rshift', '>>', '>>='), ('and', '&', '&='), ('xor', '^', '^='), ('or', '|', '|='), ('matmul', '@', '@='),
    ('divmod', 'divmod()', None),
]
"""(stem, symbol, in-place symbol) of each binary operator.  The stem 'add'
gives the methods __add__, __radd__ and __iadd__; divmod() has no in-place
form.  The symbols appear in the 'unsupported operand type(s)' messages."""


def binop_error(a: Any, b: Any, sym: str) -> TypeError:
    """The error for a binary operator neither operand supports."""
    return TypeError(f"unsupported operand type(s) for {sym}: '{type_name(a)}' and '{type_name(b)}'")


def is_subclass_override(a: Instance, b: Instance, rname: str) -> bool:
    """Whether Python would try b's reflected method `rname` before a's
    method: b's class must be a proper subclass of a's that provides a
    different `rname` than a's class does."""
    bc: Class = b.cls
    ac: Class = a.cls
    if bc is ac or ac not in bc.mro:
        return False
    return lookup(bc, rname)[1] is not lookup(ac, rname)[1]


def binary_protocol(a: Instance, b: Any, name: str, rname: str, sym: str) -> Any:
    """Evaluate a binary operator with an interpreted left operand, e.g.
    `a + b` with name '__add__' and rname '__radd__', the way Python does:

    1. a.__add__(b);
    2. otherwise b.__radd__(a), unless b has the same class as a (b may also
       be a host object, e.g. `vector + 1` tries int.__radd__);
    3. otherwise TypeError.

    A method that is missing or returns NotImplemented does not count.  When
    b's class is a subclass of a's that overrides __radd__, step 2 comes
    first (see _binary_subclass_first).
    """
    if type(b) is Instance and is_subclass_override(a, b, rname):
        return _binary_subclass_first(a, b, name, rname, sym)
    r: Any = call_special(a, name, (b,))
    if r is not MISSING and r is not NotImplemented:
        return r
    if type(b) is Instance:
        if b.cls is not a.cls:
            r = call_special(b, rname, (a,))
            if r is not MISSING and r is not NotImplemented:
                return r
    else:
        if name == '__mul__' and isinstance(b, SEQUENCE_TYPES) and not has_special(a, '__index__'):
            # `obj * 'ab'`: the host's repetition would complain about the index
            raise sequence_error(b, a, name)
        f: Any = getattr(type(b), rname, None)
        if f is not None:
            r = f(b, a)
            if r is not NotImplemented:
                return r
    raise binop_error(a, b, sym)


def _binary_subclass_first(a: Instance, b: Instance, name: str, rname: str, sym: str) -> Any:
    """binary_protocol() when b's class overrides the reflected method of a's:
    try b.__radd__(a) before a.__add__(b)."""
    r: Any = call_special(b, rname, (a,))
    if r is not MISSING and r is not NotImplemented:
        return r
    r = call_special(a, name, (b,))
    if r is not MISSING and r is not NotImplemented:
        return r
    raise binop_error(a, b, sym)


def _forward_binary(name: str, rname: str, sym: str) -> BinaryMethod:
    """Make the host method Instance.__add__ (etc.), which the host calls
    for `a + b` when a is an interpreted object."""
    def method(self: Instance, other: Any) -> Any:
        return binary_protocol(self, other, name, rname, sym)
    method.__name__ = name
    return method


def _forward_reflected(name: str, rname: str, sym: str) -> BinaryMethod:
    """Make the host method Instance.__radd__ (etc.), which the host calls for
    `a + b` when b is an interpreted object and a is a host object whose own
    __add__ returned NotImplemented."""
    def method(self: Instance, other: Any) -> Any:
        r: Any = call_special(self, rname, (other,))
        if r is MISSING or r is NotImplemented:
            return reflected_fallback(self, other, name, sym)
        return r
    method.__name__ = rname
    return method


SEQUENCE_TYPES: tuple[type, ...] = (str, list, tuple, bytes, bytearray)
"""The host sequences whose `+` and `*` are concatenation and repetition."""


def reflected_fallback(o: Instance, other: Any, name: str, sym: str) -> Any:
    """`other <op> o` where the host value other declined and o has no
    usable reflected method.  Python would still apply other's method to o
    when o's class derives from a host type (`[0] + MyList([1])`, `5 - MyInt(3)`),
    so it is applied to o's native part; then come the host sequences'
    concatenation and repetition, else the TypeError."""
    n: Any = o.native
    if n is not None:
        f: Any = getattr(type(other), name, None)
        if f is not None:
            r: Any = f(other, n)
            if r is not NotImplemented:
                return r
    if (name == '__add__' or name == '__mul__') and isinstance(other, SEQUENCE_TYPES):
        return sequence_fallback(o, other, name)
    raise binop_error(other, o, sym)


def sequence_fallback(o: Instance, seq: Any, name: str) -> Any:
    """`seq + o` or `seq * o` for a host sequence: returning NotImplemented
    lets the host repeat the sequence when o has __index__, and extend a list
    by an iterable o for `lst += o`; anything else is an error."""
    if name == '__mul__':
        if has_special(o, '__index__'):
            return NotImplemented
    elif type(seq) is list and (has_special(o, '__iter__') or has_special(o, '__getitem__')):
        return NotImplemented
    raise sequence_error(seq, o, name)


def sequence_error(seq: Any, o: Instance, name: str) -> TypeError:
    """The TypeError for concatenating (name '__add__') or repeating host
    sequence seq with instance o, which supports neither."""
    if name == '__mul__':
        return TypeError(f"can't multiply sequence by non-int of type '{type_name(o)}'")
    tn: str = sequence_base(seq).__name__
    if tn == 'bytes' or tn == 'bytearray':
        return TypeError(f"can't concat {type_name(o)} to {tn}")
    return TypeError(f'can only concatenate {tn} (not "{type_name(o)}") to {tn}')


def sequence_base(seq: Any) -> type:
    """Which of SEQUENCE_TYPES seq is an instance of."""
    for t in SEQUENCE_TYPES:
        if isinstance(seq, t):
            return t
    return type(seq)


def _forward_inplace(iname: str, name: str, rname: str, sym: str) -> BinaryMethod:
    """Make the host method Instance.__iadd__ (etc.) for `a += b`: use the
    class's __iadd__ if it has one that does not return NotImplemented, and
    fall back to `a + b` otherwise.  The in-place method of a host base
    class (list.__iadd__) returns the native part, which stands for a."""
    def method(self: Instance, other: Any) -> Any:
        r: Any = call_special(self, iname, (other,))
        if r is MISSING or r is NotImplemented:
            return binary_protocol(self, other, name, rname, sym)
        if r is not None and r is self.native:
            return self
        return r
    method.__name__ = iname
    return method


def _binary_methods() -> dict[str, BinaryMethod]:
    """The forwarding methods of every operator in BINARY_OPERATORS."""
    methods: dict[str, BinaryMethod] = {}
    for stem, sym, isym in BINARY_OPERATORS:
        name: str = f'__{stem}__'
        rname: str = f'__r{stem}__'
        methods[name] = _forward_binary(name, rname, sym)
        methods[rname] = _forward_reflected(name, rname, sym)
        if isym is not None:
            iname: str = f'__i{stem}__'
            methods[iname] = _forward_inplace(iname, name, rname, isym)
    return methods


# ---------------------------------------------------------------------------
# Rich comparisons: <, <=, >, >=, ==, !=
# ---------------------------------------------------------------------------

COMPARISONS: list[tuple[str, str, str]] = [
    ('lt', 'gt', '<'), ('le', 'ge', '<='), ('gt', 'lt', '>'), ('ge', 'le', '>='), ('eq', 'eq', '=='), ('ne', 'ne', '!='),
]
"""(stem, reflected stem, symbol) of each comparison.  The reflection of
`a < b` is `b > a`; == and != are their own reflections."""


def compare_protocol(a: Instance, b: Any, name: str, rname: str, sym: str) -> Any:
    """Evaluate a comparison with an interpreted left operand, e.g. `a < b`
    with name '__lt__' and rname '__gt__', the way Python does:

    1. a.__lt__(b);
    2. b.__gt__(a) (b may also be a host object);
    3. otherwise `==` is identity, `!=` non-identity, and the ordering
       comparisons raise TypeError.

    A method that is missing or returns NotImplemented does not count.
    When b's class is a proper subclass of a's, step 2 comes first (see
    _compare_subclass_first).
    """
    if type(b) is Instance and b.cls is not a.cls and a.cls in b.cls.mro:
        return _compare_subclass_first(a, b, name, rname, sym)
    r: Any = call_special(a, name, (b,))
    if r is not MISSING and r is not NotImplemented:
        return r
    if type(b) is Instance:
        r = call_special(b, rname, (a,))
        if r is not MISSING and r is not NotImplemented:
            return r
    else:
        f: Any = getattr(type(b), rname, None)
        if f is not None:
            r = f(b, a)
            if r is not NotImplemented:
                return r
    # the start of compare_failed(), inlined: == falling back to identity
    # is common (searching a list of instances)
    if sym == '==':
        return a is b
    if sym == '!=':
        return a is not b
    return compare_failed(a, b, sym)


def _compare_subclass_first(a: Instance, b: Instance, name: str, rname: str, sym: str) -> Any:
    """compare_protocol() when b's class is a proper subclass of a's: Python
    tries b.__gt__(a) before a.__lt__(b), whether or not the subclass
    overrides it (unlike the binary operators), and does not retry it."""
    r: Any = call_special(b, rname, (a,))
    if r is not MISSING and r is not NotImplemented:
        return r
    r = call_special(a, name, (b,))
    if r is not MISSING and r is not NotImplemented:
        return r
    return compare_failed(a, b, sym)


def compare_failed(a: Instance, b: Any, sym: str) -> Any:
    """The result of comparison `a sym b` when neither operand implements
    it: identity for == and !=, a TypeError for the ordering comparisons."""
    if sym == '==':
        return a is b
    if sym == '!=':
        return a is not b
    raise TypeError(f"'{sym}' not supported between instances of '{type_name(a)}' and '{type_name(b)}'")


def _forward_compare(name: str, rname: str, sym: str) -> BinaryMethod:
    """Make the host method Instance.__lt__ (etc.), which the host calls for
    `a < b` when a is an interpreted object.  The host also calls it as the
    reflection of `x > a` when x is a host object that cannot compare itself
    with a."""
    def method(self: Instance, other: Any) -> Any:
        return compare_protocol(self, other, name, rname, sym)
    method.__name__ = name
    return method


def _compare_methods() -> dict[str, BinaryMethod]:
    """The forwarding methods of every comparison in COMPARISONS."""
    methods: dict[str, BinaryMethod] = {}
    for stem, rstem, sym in COMPARISONS:
        name: str = f'__{stem}__'
        methods[name] = _forward_compare(name, f'__{rstem}__', sym)
    return methods


def _native_operand_methods() -> dict[str, int]:
    """The names of the operator methods (binary, reflected, in-place,
    comparisons and __contains__) whose operands call_special() passes to
    a host base class's method as native parts."""
    names: dict[str, int] = {'__contains__': 1}
    for stem, _, _ in BINARY_OPERATORS:
        names[f'__{stem}__'] = 1
        names[f'__r{stem}__'] = 1
        names[f'__i{stem}__'] = 1
    for stem, _, _ in COMPARISONS:
        names[f'__{stem}__'] = 1
    return names


NATIVE_OPERAND_METHODS: dict[str, int] = _native_operand_methods()
"""See _native_operand_methods (used as a set)."""


# ---------------------------------------------------------------------------
# Methods without arguments that are simply forwarded: -x, abs(x),
# operator.index(x), math.trunc(x), next(x), ...
# ---------------------------------------------------------------------------

UNARY_METHODS: list[tuple[str, str]] = [
    ('neg', "bad operand type for unary -: '{}'"),
    ('pos', "bad operand type for unary +: '{}'"),
    ('invert', "bad operand type for unary ~: '{}'"),
    ('abs', "bad operand type for abs(): '{}'"),
    ('index', "'{}' object cannot be interpreted as an integer"),
    ('trunc', "type {} doesn't define __trunc__ method"),
    ('next', "'{}' object is not an iterator"),
]
"""(stem, error message) of each method that is simply forwarded; the
message, formatted with the class name, is the TypeError raised when the
class does not define the method."""


def _forward_unary(name: str, message: str) -> UnaryMethod:
    """Make a host method of Instance that forwards to the interpreted
    method `name`, raising TypeError(message) if the class lacks it."""
    def method(self: Instance) -> Any:
        r: Any = call_special(self, name, ())
        if r is MISSING:
            raise TypeError(message.format(self.cls.__name__))
        return r
    method.__name__ = name
    return method


def _unary_methods() -> dict[str, UnaryMethod]:
    """The forwarding methods of every method in UNARY_METHODS."""
    methods: dict[str, UnaryMethod] = {}
    for stem, message in UNARY_METHODS:
        name: str = f'__{stem}__'
        methods[name] = _forward_unary(name, message)
    return methods


# ---------------------------------------------------------------------------
# Methods with rules of their own
# ---------------------------------------------------------------------------

def _inst_repr(self: Instance) -> str:
    """repr(x): the result must be a str."""
    r: Any = call_special(self, '__repr__', ())
    if type(r) is not str:
        return str_result(r, '__repr__')
    return r


def _inst_str(self: Instance) -> str:
    """str(x): the result must be a str (object.__str__ falls back to repr)."""
    r: Any = call_special(self, '__str__', ())
    if type(r) is not str:
        return str_result(r, '__str__')
    return r


def str_result(r: Any, name: str) -> str:
    """The result r of a __repr__ or __str__ method (name) that is not
    exactly a str: an instance of a str subclass is accepted (as its native
    str when the subclass is interpreted), anything else is an error."""
    if isinstance(r, str):
        return r
    if type(r) is Instance and isinstance(r.native, str):
        return r.native
    raise TypeError(f'{name} returned non-string (type {type_name(r)})')


def _inst_format(self: Instance, spec: str) -> Any:
    """format(x, spec) and f-strings.  The __format__ of int, float, str, ...
    makes an empty spec mean str(x), which for an instance of an interpreted
    subclass must see the subclass's __str__."""
    if not spec and self.native is not None and lookup(self.cls, '__format__')[0] is K_NATIVE:
        return _inst_str(self)
    return call_special(self, '__format__', (spec,))


def _inst_hash(self: Instance) -> int:
    """hash(x): a class with `__hash__ = None` (which a class defining __eq__
    but not __hash__ gets implicitly) is unhashable; the result must be an int."""
    e: Entry = lookup(self.cls, '__hash__')
    if e[1] is None:
        raise TypeError(f"unhashable type: '{self.cls.__name__}'")
    r: Any = call_special(self, '__hash__', ())
    if type(r) is not int and not isinstance(r, int):
        raise TypeError('__hash__ method should return an integer')
    return r


def _inst_bool(self: Instance) -> bool:
    """Truth testing (`if x:`, `not x`, bool(x)): __bool__, which must return
    a bool, else __len__() != 0, else true.  (Set to None, either method
    raises "'NoneType' object is not callable", as in Python.)"""
    r: Any = call_special(self, '__bool__', ())
    if r is MISSING:
        r = call_special(self, '__len__', ())
        if r is MISSING:
            return True
        if type(r) is not int or not 0 <= r <= MAX_LEN:
            r = len_result(r)
        return r != 0
    if type(r) is not bool:
        raise TypeError(f'__bool__ should return bool, returned {type_name(r)}')
    return r


MAX_LEN: int = sys.maxsize
"""The largest length (and index) the host supports."""


def len_result(r: Any) -> int:
    """Check a value returned by __len__ the way len() does: it must be
    an integer (or have __index__) that fits in a C ssize_t and is >= 0."""
    n: int = operator.index(r)
    if n > MAX_LEN or n < -MAX_LEN - 1:
        raise OverflowError("cannot fit 'int' into an index-sized integer")
    if n < 0:
        raise ValueError('__len__() should return >= 0')
    return n


def _inst_len(self: Instance) -> Any:
    """len(x); the host checks that the result is a non-negative int."""
    r: Any = call_special(self, '__len__', ())
    if r is MISSING:
        raise TypeError(f"object of type '{self.cls.__name__}' has no len()")
    return r


class SeqView:
    """A host object standing for an interpreted instance that has
    __getitem__ (and maybe __len__) but no __iter__ or __reversed__, so that
    the host's own sequence iterator and reversed() can walk it: they stop
    at IndexError (or StopIteration) and give CPython's errors."""

    __slots__ = ('obj',)

    def __init__(self, obj: Any) -> None:
        self.obj: Any = obj

    def __getitem__(self, i: int) -> Any:
        return self.obj[i]

    def __len__(self) -> int:
        return len(self.obj)


def blocked_error(o: Instance, name: str, message: str) -> TypeError | None:
    """The TypeError(message) to raise instead of the "'NoneType' object is
    not callable" that calling special method `name` of o gave, if the
    class sets it to None to block it, else None."""
    if special_is_none(o, name):
        return TypeError(message.format(o.cls.__name__))
    return None


def _inst_iter(self: Instance) -> Any:
    """iter(x) and for loops: __iter__, else the old sequence protocol.
    The result must be an iterator."""
    try:
        r: Any = call_special(self, '__iter__', ())
    except TypeError:
        err: TypeError | None = blocked_error(self, '__iter__', "'{}' object is not iterable")
        if err is not None:
            raise err from None
        raise
    if r is MISSING:
        if has_special(self, '__getitem__'):
            return iter(SeqView(self))
        raise TypeError(f"'{self.cls.__name__}' object is not iterable")
    if type(r) is Instance and not has_special(r, '__next__'):
        # the host accepts any Instance, since Instance defines __next__
        raise TypeError(f"iter() returned non-iterator of type '{r.cls.__name__}'")
    return r


def _inst_reversed(self: Instance) -> Any:
    """reversed(x): __reversed__, else x[len(x) - 1], ..., x[0] for a class
    with __getitem__."""
    try:
        r: Any = call_special(self, '__reversed__', ())
    except TypeError:
        err: TypeError | None = blocked_error(self, '__reversed__', "'{}' object is not reversible")
        if err is not None:
            raise err from None
        raise
    if r is MISSING:
        if has_special(self, '__getitem__'):
            return reversed(SeqView(self))
        raise TypeError(f"'{self.cls.__name__}' object is not reversible")
    return r


def _inst_contains(self: Instance, x: Any) -> bool:
    """`x in self`: __contains__ (result converted to bool), else a search by
    iteration comparing with `is` and then `==`."""
    try:
        r: Any = call_special(self, '__contains__', (x,))
    except TypeError:
        err: TypeError | None = blocked_error(self, '__contains__', "'{}' object is not a container")
        if err is not None:
            raise err from None
        raise
    if r is MISSING:
        return contains_by_iteration(self, x)
    return bool(r)


def contains_by_iteration(o: Instance, x: Any) -> bool:
    """`x in o` for an instance without __contains__: search its items."""
    # Instance.__iter__ is installed at run time, so the type checker needs
    # to be told that the host can iterate o
    items: Any = o
    try:
        it: Iterator[Any] = iter(items)
    except TypeError:
        raise TypeError(f"argument of type '{o.cls.__name__}' is not iterable") from None
    for y in it:
        if y is x or y == x:
            return True
    return False


def _inst_getitem(self: Instance, key: Any) -> Any:
    """self[key].  For a dict subclass, a missing key calls __missing__."""
    try:
        r: Any = call_special(self, '__getitem__', (key,))
        if r is MISSING:
            raise TypeError(f"'{self.cls.__name__}' object is not subscriptable")
        return r
    except KeyError:
        m: Any = missing_method(self)
        if m is None:
            raise
    # called here, outside the handler, so that its errors are not chained
    return call(m, (key,), None)


def missing_method(o: Instance) -> Any:
    """The bound __missing__ method of instance o of a dict subclass, which
    `o[key]` calls when dict's own __getitem__ does not find the key (the
    native dict cannot call it), or None."""
    if not isinstance(o.native, dict) or lookup(o.cls, '__getitem__')[0] is not K_NATIVE:
        return None
    e: Entry = lookup(o.cls, '__missing__')
    if e[0] is K_MISSING or e[0] is K_NODICT or e[0] is K_NATIVE:
        return None
    return bind_value(e[1], e[0], o, o.cls)


def _inst_setitem(self: Instance, key: Any, value: Any) -> None:
    """self[key] = value."""
    r: Any = call_special(self, '__setitem__', (key, value))
    if r is MISSING:
        raise TypeError(f"'{self.cls.__name__}' object does not support item assignment")


def _inst_delitem(self: Instance, key: Any) -> None:
    """del self[key]."""
    r: Any = call_special(self, '__delitem__', (key,))
    if r is MISSING:
        raise TypeError(f"'{self.cls.__name__}' object doesn't support item deletion")


def _inst_call(self: Instance, *args: Any, **kw: Any) -> Any:
    """self(...) from host code, e.g. an interpreted callable object passed
    as a key function to sorted()."""
    return call(self, args, kw or None)


def _inst_int(self: Instance) -> Any:
    """int(x): __int__, else __index__, else __trunc__."""
    r: Any = call_special(self, '__int__', ())
    if r is MISSING:
        r = call_special(self, '__index__', ())
        if r is not MISSING and not isinstance(r, int):
            raise TypeError(f'__index__ returned non-int (type {type_name(r)})')
        if r is MISSING:
            r = call_special(self, '__trunc__', ())
            if r is MISSING:
                raise TypeError("int() argument must be a string, a bytes-like object or a real number, "
                                f"not '{self.cls.__name__}'")
    return r


def _inst_float(self: Instance) -> Any:
    """float(x): __float__, else float(__index__())."""
    r: Any = call_special(self, '__float__', ())
    if r is MISSING:
        r = call_special(self, '__index__', ())
        if r is MISSING:
            raise TypeError(f"float() argument must be a string or a real number, not '{self.cls.__name__}'")
        return float(r)
    if type(r) is not float and not isinstance(r, float):
        raise TypeError(f'{self.cls.__name__}.__float__ returned non-float (type {type_name(r)})')
    return r


def real_value(o: Instance) -> float:
    """o as a float for math.floor(), math.ceil() and complex() when its
    class lacks the specific method: by __float__, else __index__."""
    if has_special(o, '__float__') or has_special(o, '__index__'):
        # Instance.__float__ is installed at run time
        x: Any = o
        return float(x)
    raise TypeError(f'must be real number, not {o.cls.__name__}')


def _inst_floor(self: Instance) -> Any:
    """math.floor(x): __floor__, else the floor of x as a float."""
    r: Any = call_special(self, '__floor__', ())
    if r is MISSING:
        return math.floor(real_value(self))
    return r


def _inst_ceil(self: Instance) -> Any:
    """math.ceil(x): __ceil__, else the ceiling of x as a float."""
    r: Any = call_special(self, '__ceil__', ())
    if r is MISSING:
        return math.ceil(real_value(self))
    return r


def _inst_complex(self: Instance) -> Any:
    """complex(x): __complex__, else x as a float (__float__ or __index__)."""
    r: Any = call_special(self, '__complex__', ())
    if r is MISSING:
        if has_special(self, '__float__') or has_special(self, '__index__'):
            return complex(real_value(self))
        raise TypeError(f"complex() first argument must be a string or a number, not '{self.cls.__name__}'")
    return r


def _inst_bytes(self: Instance) -> Any:
    """bytes(x): __bytes__, else that many zero bytes for an object with
    __index__, else the bytes of its items."""
    r: Any = call_special(self, '__bytes__', ())
    if r is MISSING:
        # Instance.__index__ and __iter__ are installed at run time
        x: Any = self
        if has_special(self, '__index__'):
            return bytes(operator.index(x))
        if has_special(self, '__iter__') or has_special(self, '__getitem__'):
            return bytes(list(x))
        raise TypeError(f"cannot convert '{self.cls.__name__}' object to bytes")
    return r


def _inst_length_hint(self: Instance) -> Any:
    """operator.length_hint(x) (also used by list(x) and friends) when len(x)
    fails: __length_hint__, else NotImplemented (no hint)."""
    r: Any = call_special(self, '__length_hint__', ())
    if r is MISSING:
        return NotImplemented
    return r


def _inst_round(self: Instance, *args: Any) -> Any:
    """round(x) and round(x, ndigits)."""
    r: Any = call_special(self, '__round__', args)
    if r is MISSING:
        raise TypeError(f"type {self.cls.__name__} doesn't define __round__ method")
    return r


def _inst_pow3(self: Instance, other: Any, mod: Any = None) -> Any:
    """x ** y and pow(x, y, mod).  The three-argument form calls
    __pow__(y, mod) and has no reflected fallback."""
    if mod is None:
        return binary_protocol(self, other, '__pow__', '__rpow__', '** or pow()')
    r: Any = call_special(self, '__pow__', (other, mod))
    if r is MISSING or r is NotImplemented:
        raise TypeError("unsupported operand type(s) for ** or pow(): "
                        f"'{type_name(self)}', '{type_name(other)}', '{type_name(mod)}'")
    return r


def _inst_exit(self: Instance, *args: Any) -> Any:
    """__exit__(exc_type, exc_value, traceback) of a context manager used by
    host code (the compiler's `with` uses context_methods() instead).  The
    host passes host exceptions, which are mapped to the interpreted ones.

    Host code that recognizes context managers by `type(x).__exit__`
    (contextlib.ExitStack.push) finds this method on every Instance; for an
    object without __exit__ it would call the object itself."""
    if len(args) == 3 and isinstance(args[1], BaseException):
        args = exc_triple(args)
    r: Any = call_special(self, '__exit__', args)
    if r is MISSING:
        if has_special(self, '__call__'):
            return call(self, args, None)
        raise TypeError(f"'{self.cls.__name__}' object does not support the context manager protocol")
    return r


def _inst_enter(self: Instance) -> Any:
    """__enter__() of a context manager used by host code; the error is the
    one contextlib.ExitStack.enter_context reports, with the qualified name."""
    r: Any = call_special(self, '__enter__', ())
    if r is MISSING:
        cls: Class = self.cls
        raise TypeError(f"'{cls.__module__}.{cls.__qualname__}' object does not support the context manager protocol")
    return r


def _inst_getattr(self: Instance, name: str) -> Any:
    """Attribute reads by host code (for example functools.wraps or
    operator.attrgetter) of a name that is not one of Instance's own slots
    or methods: resolve it the way interpreted code would."""
    return inst_getattr(self, name)


def _inst_copy(self: Instance) -> Any:
    """copy.copy(x): __copy__, else a shallow copy of the instance's state
    (and of its native part), or the pickle protocol if the class customizes
    it (see copy_by_reduce)."""
    r: Any = call_special(self, '__copy__', ())
    if r is MISSING:
        if customizes_reduce(self.cls):
            return copy_by_reduce(self, None)
        new: Instance = Instance(self.cls)
        if self.native is not None:
            new.native = copy_native(self.native, new)
        new.d.update(self.d)
        if self.sv is not None:
            new.sv = self.sv.copy()
        return new
    return r


def copy_native(n: Any, new: Instance) -> Any:
    """A shallow copy of native part n for `new`, the copy of its instance
    (a native exception refers back to the instance it belongs to)."""
    import copy
    r: Any = copy.copy(n)
    if isinstance(r, BaseException):
        setattr(r, INST_KEY, new)
    return r


def _inst_deepcopy(self: Instance, memo: dict[int, Any]) -> Any:
    """copy.deepcopy(x): __deepcopy__, else a deep copy of the instance's
    state, or the pickle protocol if the class customizes it."""
    r: Any = call_special(self, '__deepcopy__', (memo,))
    if r is MISSING:
        import copy
        if customizes_reduce(self.cls):
            return copy_by_reduce(self, memo)
        new: Instance = Instance(self.cls)
        memo[id(self)] = new
        new.native = copy.deepcopy(self.native, memo)
        new.d.update(copy.deepcopy(self.d, memo))
        if self.sv is not None:
            new.sv = copy.deepcopy(self.sv, memo)
        return new
    return r


REDUCE_METHODS: tuple[str, ...] = ('__reduce_ex__', '__reduce__', '__getstate__', '__setstate__')
"""The methods of the pickle protocol, which the copy module also uses."""


def customizes_reduce(c: Class) -> bool:
    """Whether interpreted class c (not object or a host base class)
    defines one of REDUCE_METHODS."""
    for name in REDUCE_METHODS:
        if defines_special(c, name):
            return True
    return False


def defines_special(c: Class, name: str) -> bool:
    """Whether an interpreted class in the MRO of c defines `name`."""
    k: Signal = lookup(c, name)[0]
    return k is not K_MISSING and k is not K_NODICT and k is not K_NATIVE and k is not K_EMU


def copy_by_reduce(o: Instance, memo: dict[int, Any] | None) -> Any:
    """Copy o (deeply if memo is given) the way the copy module copies host
    objects, by rebuilding it from what o.__reduce_ex__(4) returns."""
    import copy
    rv: Any = reduce_instance(o, memo is not None)
    if isinstance(rv, str):
        return o
    # the copy module's own rebuilding step, which it does not export
    reconstruct: Any = copy.__dict__['_reconstruct']
    return reconstruct(o, memo, *rv)


def reduce_instance(o: Instance, deep: bool) -> Any:
    """o.__reduce_ex__(4): the class's __reduce_ex__ or __reduce__, else what
    object's would give: rebuild an instance around (a copy of) o's native
    part and restore the state from __getstate__ (passing it to
    __setstate__, if the class has one)."""
    from .object_methods import copy_instance_reconstruct
    c: Class = o.cls
    if defines_special(c, '__reduce_ex__'):
        return call_special(o, '__reduce_ex__', (4,))
    if defines_special(c, '__reduce__'):
        return call_special(o, '__reduce__', ())
    n: Any = o.native
    if n is not None and not deep:
        import copy
        n = copy.copy(n)
    return (copy_instance_reconstruct, (c, n), call_special(o, '__getstate__', ()))


def _inst_replace(self: Instance, **changes: Any) -> Any:
    """copy.replace(x, **changes): the class's __replace__."""
    if not has_special(self, '__replace__'):
        raise TypeError(f'replace() does not support {self.cls.__name__} objects')
    return call(inst_getattr(self, '__replace__'), (), changes or None)


# ---------------------------------------------------------------------------
# Installing the forwarding methods on Instance
# ---------------------------------------------------------------------------

INSTANCE_METHODS: dict[str, Callable[..., Any]] = {}
"""Every host special method installed on Instance, by name: the generated
operator forwarders and the methods with rules of their own."""
INSTANCE_METHODS.update(_binary_methods())
INSTANCE_METHODS.update(_compare_methods())
INSTANCE_METHODS.update(_unary_methods())
INSTANCE_METHODS.update({
    '__repr__': _inst_repr,
    '__str__': _inst_str,
    '__format__': _inst_format,
    '__hash__': _inst_hash,
    '__bool__': _inst_bool,
    '__len__': _inst_len,
    '__iter__': _inst_iter,
    '__reversed__': _inst_reversed,
    '__contains__': _inst_contains,
    '__getitem__': _inst_getitem,
    '__setitem__': _inst_setitem,
    '__delitem__': _inst_delitem,
    '__call__': _inst_call,
    '__int__': _inst_int,
    '__float__': _inst_float,
    '__floor__': _inst_floor,
    '__ceil__': _inst_ceil,
    '__complex__': _inst_complex,
    '__bytes__': _inst_bytes,
    '__length_hint__': _inst_length_hint,
    '__round__': _inst_round,
    '__enter__': _inst_enter,
    '__exit__': _inst_exit,
    '__getattr__': _inst_getattr,
    '__copy__': _inst_copy,
    '__deepcopy__': _inst_deepcopy,
    '__replace__': _inst_replace,
    # replaces the generated binary __pow__, since pow() also takes a modulus
    '__pow__': _inst_pow3,
})


def install_methods(cls: Any, methods: dict[str, Callable[..., Any]]) -> None:
    """Store each of `methods` on class cls under its name."""
    for name, method in methods.items():
        setattr(cls, name, method)


install_methods(Instance, INSTANCE_METHODS)


class InstanceGet:
    """Instance.__get__: makes an interpreted object found in the dict of a
    host class a descriptor for host code when its class defines __get__.
    This binds the methods of a class made by a host metaclass (an enum, a
    NamedTuple) when boros runs itself: they are instances of the inner
    interpreter's Function class.  Reading the attribute raises
    AttributeError when the class has no __get__ (and on Instance itself),
    so hasattr() and inspect do not mistake other objects for descriptors."""

    def __get__(self, inst: Instance | None, owner: Any = None) -> Any:
        if inst is None or not has_special(inst, '__get__'):
            raise AttributeError('__get__')
        return inst_getattr(inst, '__get__')

    # the host's descriptor slot calls this directly, with (inst, obj, type)
    def __call__(self, inst: Instance, obj: Any, owner: Any = None) -> Any:
        r: Any = call_special(inst, '__get__', (obj, owner))
        if r is MISSING:
            return inst
        return r


install_methods(Instance, {'__get__': InstanceGet()})


# ---------------------------------------------------------------------------
# Helpers for compiled code: with, async with, await, async for
# ---------------------------------------------------------------------------

def context_methods(mgr: Any) -> tuple[Callable[[], Any], Callable[..., Any]]:
    """The (enter, exit) callables of the context manager of a `with`
    statement: the statement calls enter() before its body and
    exit(exc_type, exc_value, traceback) after it.  As in Python, both
    methods are looked up on the type, before either is called."""
    if type(mgr) is Instance:
        e1: Entry = lookup(mgr.cls, '__enter__')
        e2: Entry = lookup(mgr.cls, '__exit__')
        if e1[0] is K_MISSING or e2[0] is K_MISSING or e1[0] is K_NODICT or e2[0] is K_NODICT:
            raise not_context_manager(mgr.cls.__name__, has_special(mgr, '__enter__'))
        enter: Any = bind_value(e1[1], e1[0], mgr, mgr.cls)
        exit_: Any = bind_value(e2[1], e2[0], mgr, mgr.cls)
        return (lambda: call(enter, (), None)), (lambda *a: call(exit_, a, None))
    t: type = type(mgr)
    if not hasattr(t, '__enter__') or not hasattr(t, '__exit__'):
        raise not_context_manager(type_name(mgr), hasattr(t, '__enter__'))
    return mgr.__enter__, mgr.__exit__


def not_context_manager(name: str, has_enter: bool) -> TypeError:
    """The error for a `with` statement on an object of type `name` that
    lacks __enter__ or (if has_enter) __exit__."""
    missed: str = ' (missed __exit__ method)' if has_enter else ''
    return TypeError(f"'{name}' object does not support the context manager protocol{missed}")


def async_context_methods(mgr: Any) -> tuple[Callable[[], Any], Callable[..., Any]]:
    """The (aenter, aexit) callables of the context manager of an `async
    with` statement; the awaitables they return are awaited with await_iter().
    As for `with`, both methods are looked up on the type first."""
    if type(mgr) is Instance:
        e1: Entry = lookup(mgr.cls, '__aenter__')
        e2: Entry = lookup(mgr.cls, '__aexit__')
        check_async_context_manager(mgr.cls.__name__, e1[0] is not K_MISSING, e2[0] is not K_MISSING)
        enter: Any = bind_value(e1[1], e1[0], mgr, mgr.cls)
        exit_: Any = bind_value(e2[1], e2[0], mgr, mgr.cls)
        return (lambda: call(enter, (), None)), (lambda *a: call(exit_, a, None))
    t: type = type(mgr)
    check_async_context_manager(type_name(mgr), hasattr(t, '__aenter__'), hasattr(t, '__aexit__'))
    return mgr.__aenter__, mgr.__aexit__


def check_async_context_manager(name: str, has_aenter: bool, has_aexit: bool) -> None:
    """The TypeError for an `async with` on an object of type `name` that
    lacks __aenter__ or __aexit__."""
    if not has_aenter:
        raise TypeError(f"'{name}' object does not support the asynchronous context manager protocol")
    if not has_aexit:
        raise TypeError(f"'{name}' object does not support the asynchronous context manager protocol "
                        '(missed __aexit__ method)')


def exc_type(v: Any) -> Any:
    """The class of exception value v, which `with` passes to __exit__."""
    if type(v) is Instance:
        return v.cls
    return type(v)


CO_ITERABLE_COROUTINE: int = 0x100
"""The code flag of a generator decorated with types.coroutine, which may be awaited."""


def await_iter(v: Any) -> Iterator[Any]:
    """The iterator that `await v` delegates to with `yield from`: v.__await__()."""
    t: type = type(v)
    if t is Instance:
        r: Any = call_special(v, '__await__', ())
        if r is MISSING:
            raise TypeError(f"object {v.cls.__name__} can't be used in 'await' expression")
        return r
    m: Any = getattr(t, '__await__', None)
    if m is None:
        if isinstance(v, types.GeneratorType) and v.gi_code.co_flags & CO_ITERABLE_COROUTINE:
            return v
        raise TypeError(f"object {type_name(v)} can't be used in 'await' expression")
    return m(v)


def aiter_of(v: Any) -> Any:
    """aiter(v), used by `async for`: the asynchronous iterator, which must
    have an __anext__ method."""
    if type(v) is Instance:
        it: Any = call_special(v, '__aiter__', ())
        if it is MISSING:
            raise TypeError(f"'async for' requires an object with __aiter__ method, got {v.cls.__name__}")
    else:
        m: Any = getattr(type(v), '__aiter__', None)
        if m is None:
            raise TypeError(f"'async for' requires an object with __aiter__ method, got {type_name(v)}")
        it = m(v)
    if not (has_special(it, '__anext__') if type(it) is Instance else hasattr(type(it), '__anext__')):
        raise TypeError("'async for' received an object from __aiter__ that does not implement __anext__: "
                        f'{type_name(it)}')
    return it


def anext_of(it: Any) -> Any:
    """anext(it) without a default: the awaitable for the next item of an
    `async for` loop."""
    if type(it) is Instance:
        return call_special(it, '__anext__', ())
    return type(it).__anext__(it)


def anext_awaitable(it: Any) -> Iterator[Any]:
    """The iterator that `async for` awaits for the next item of the
    asynchronous iterator it (StopAsyncIteration at the end)."""
    a: Any = anext_of(it)
    try:
        return await_iter(a)
    except TypeError as e:
        raise TypeError(f"'async for' received an invalid object from __anext__: {type_name(a)}") from e


# ---------------------------------------------------------------------------
# Host code awaiting interpreted objects
# ---------------------------------------------------------------------------
#
# asyncio.gather(), aiter(), anext(), contextlib.AsyncExitStack ... look the
# asynchronous special methods up on the host type, Instance.  As with the
# __iter__ and __next__ forwarders, host ABC checks (inspect.isawaitable,
# collections.abc.AsyncIterator) are then true for every Instance.

def _inst_await(self: Instance) -> Any:
    """Host code awaiting an interpreted awaitable."""
    r: Any = call_special(self, '__await__', ())
    if r is MISSING:
        raise TypeError(f"object {self.cls.__name__} can't be used in 'await' expression")
    return r


def _inst_aiter(self: Instance) -> Any:
    """aiter() of an interpreted asynchronous iterable."""
    r: Any = call_special(self, '__aiter__', ())
    if r is MISSING:
        raise TypeError(f"'{self.cls.__name__}' object is not an async iterable")
    return r


def _inst_anext(self: Instance) -> Any:
    """anext() of an interpreted asynchronous iterator."""
    r: Any = call_special(self, '__anext__', ())
    if r is MISSING:
        raise TypeError(f"'{self.cls.__name__}' object is not an async iterator")
    return r


def _inst_aenter(self: Instance) -> Any:
    """__aenter__ of an interpreted asynchronous context manager used by host code."""
    r: Any = call_special(self, '__aenter__', ())
    if r is MISSING:
        raise TypeError(f"'{self.cls.__name__}' object does not support the asynchronous context manager protocol")
    return r


def _inst_aexit(self: Instance, *args: Any) -> Any:
    """__aexit__(exc_type, exc_value, traceback) called by host code, which
    passes the host exception standing for an interpreted one."""
    if len(args) == 3 and args[1] is not None and type(args[1]) is not Instance:
        v: Any = exc_value(args[1])
        if v is not args[1]:
            args = (v.cls, v, args[2])
    r: Any = call_special(self, '__aexit__', args)
    if r is MISSING:
        raise TypeError(f"'{self.cls.__name__}' object does not support the asynchronous context manager protocol")
    return r


install_methods(Instance, {'__await__': _inst_await, '__aiter__': _inst_aiter, '__anext__': _inst_anext,
                           '__aenter__': _inst_aenter, '__aexit__': _inst_aexit})
