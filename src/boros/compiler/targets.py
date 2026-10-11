"""Compilation of assignment and deletion targets.

An assignment target compiles into a store function `store(fr, value)`;
the statement compilers evaluate the right-hand side and pass the value to
it.  Targets can be variables, attributes (`obj.x`), subscripts (`obj[k]`)
or, recursively, tuples and lists of targets with at most one starred
element (`a, *rest = value`), which unpack the value.  `del` targets
compile into statement closures in the same way.
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

from ..lexer import syntax_error
from ..runtime.attributes import delattr_any, inst_setattr, setattr_any
from ..runtime.errors import unbound_free, unpack_error
from ..runtime.objects import Instance
from ..runtime.typechecks import is_iterable_type, type_name
from ..syntax import Attribute, List, Name, Starred, Subscript, Tuple
from .names import del_name, store_name
from .scopes import LOCAL

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from ..core_types import ExprFn, Frame, StmtFn, StoreFn
    from ..syntax import Expression
    from .compiler import Compiler


def unpack(v: Any, n: int) -> Sequence[Any]:
    """The items of iterable v, checking that there are exactly n of them.

    Tuples and lists are returned as they are; other iterables are consumed
    one item past n so that too many values are detected without exhausting
    an infinite iterator.
    """
    t: type = type(v)
    if t is tuple or t is list:
        if len(v) != n:
            raise unpack_error(len(v), n)
        return v
    try:
        it: Iterator[Any] = iter(v)
    except TypeError:
        if is_iterable_type(v):
            raise
        raise TypeError(f'cannot unpack non-iterable {type_name(v)} object') from None
    items: list[Any] = list(itertools.islice(it, n + 1))
    if len(items) < n:
        raise unpack_error(len(items), n)
    if len(items) > n:
        raise ValueError(f'too many values to unpack (expected {n})')
    return items


# -- assignment targets ----------------------------------------------------------

def target(comp: Compiler, t: Expression) -> StoreFn:
    """Compile an assignment target into a function store(fr, value)."""
    if type(t) is Name:
        return store_name(comp, t.id)
    if type(t) is Attribute:
        return make_store_attr(comp.expr(t.value), t.attr)
    if type(t) is Subscript:
        return subscript_target(comp, t)
    if type(t) is Tuple or type(t) is List:
        return unpack_target(comp, t.elts)
    if type(t) is Starred:
        raise syntax_error('starred assignment target must be in a list or tuple', comp.filename, t.line)
    raise syntax_error(f'cannot assign to {type(t).__name__}', comp.filename, t.line)


def make_store_attr(oc: ExprFn, name: str) -> StoreFn:
    """`obj.name = value`, with a direct path for interpreted instances."""
    def store_attr(fr: Frame, v: Any) -> None:
        o: Any = oc(fr)
        if type(o) is Instance:
            inst_setattr(o, name, v)
        else:
            setattr_any(o, name, v)
    return store_attr


def subscript_target(comp: Compiler, t: Subscript) -> StoreFn:
    """Compile `obj[key] = value`.  When obj is a parameter and the key a
    constant or a free variable of the enclosing function, both are read
    inline."""
    ok, oname = comp.operand(t.value)
    kk, k = comp.operand(t.index)
    if ok == 'param':
        if kk == 'free1':
            return make_store_item_param_free(oname, k)
        if kk == 'const':
            return make_store_item_param_const(oname, k)
    oc: ExprFn = comp.expr(t.value)
    ic: ExprFn = comp.expr(t.index)
    return make_store_item(oc, ic)


def make_store_item_param_free(oname: str, k: str) -> StoreFn:
    """`param[free_variable] = value`."""
    def store_item_pf(fr: Frame, v: Any) -> None:
        try:
            key: Any = fr['.up'][k]
        except KeyError:
            raise unbound_free(k) from None
        fr[oname][key] = v
    return store_item_pf


def make_store_item_param_const(oname: str, k: Any) -> StoreFn:
    """`param[constant] = value`."""
    def store_item_pc(fr: Frame, v: Any) -> None:
        fr[oname][k] = v
    return store_item_pc


def make_store_item(oc: ExprFn, ic: ExprFn) -> StoreFn:
    """`obj[key] = value` (obj is evaluated before key, as in CPython)."""
    def store_item(fr: Frame, v: Any) -> None:
        o: Any = oc(fr)
        o[ic(fr)] = v
    return store_item


# -- unpacking -------------------------------------------------------------------------

def unpack_target(comp: Compiler, elts: list[Expression]) -> StoreFn:
    """Compile a tuple or list target `a, b, *c, d`: a store function that
    unpacks the value and stores each item into the matching target."""
    star, stores = element_stores(comp, elts)
    if star >= 0:
        return make_unpack_star(stores, star)
    n: int = len(stores)
    names: list[str] = [e.id for e in elts if type(e) is Name and comp.resolve(e.id)[0] is LOCAL]
    if len(names) == n:
        return make_unpack_locals(names, n)
    if n == 2:
        return make_unpack2(stores[0], stores[1])
    return make_unpack_n(stores, n)


def element_stores(comp: Compiler, elts: list[Expression]) -> tuple[int, list[StoreFn]]:
    """Compile the elements of an unpacking target.  Returns the index of
    the starred element (or -1 if there is none) and one store function per
    element (for the starred one, the store of the target inside the star)."""
    stores: list[StoreFn] = []
    star: int = -1
    for i, e in enumerate(elts):
        if type(e) is Starred:
            if star >= 0:
                raise SyntaxError('multiple starred expressions in assignment')
            star = i
            stores.append(target(comp, e.value))
        else:
            stores.append(target(comp, e))
    return star, stores


def make_unpack_locals(names: list[str], n: int) -> StoreFn:
    """`a, b, c = value` where every target is a local variable: all items
    are stored into the frame with a single dict update."""
    def unpack_locals(fr: Frame, v: Any) -> None:
        fr.update(zip(names, unpack(v, n)))
    return unpack_locals


def make_unpack2(s0: StoreFn, s1: StoreFn) -> StoreFn:
    """`x, y = value` for any two targets."""
    def unpack2(fr: Frame, v: Any) -> None:
        items: Sequence[Any] = unpack(v, 2)
        s0(fr, items[0])
        s1(fr, items[1])
    return unpack2


def make_unpack_n(stores: list[StoreFn], n: int) -> StoreFn:
    """`x, y, z, ... = value` for n targets without a star."""
    def unpack_n(fr: Frame, v: Any) -> None:
        items: Sequence[Any] = unpack(v, n)
        for i, s in enumerate(stores):
            s(fr, items[i])
    return unpack_n


def make_unpack_star(stores: list[StoreFn], star: int) -> StoreFn:
    """`a, *rest, z = value`: the targets before and after the star take
    one item each and the starred target takes a list of the rest."""
    n: int = len(stores)
    before: int = star
    after: int = n - star - 1

    def unpack_star(fr: Frame, v: Any) -> None:
        try:
            items: list[Any] = list(v)
        except TypeError:
            if is_iterable_type(v):
                raise
            raise TypeError(f'cannot unpack non-iterable {type_name(v)} object') from None
        m: int = len(items)
        if m < n - 1:
            raise ValueError(f'not enough values to unpack (expected at least {n - 1}, got {m})')
        i: int = 0
        while i < before:
            stores[i](fr, items[i])
            i += 1
        stores[star](fr, items[before:m - after])
        j: int = 0
        while j < after:
            stores[star + 1 + j](fr, items[m - after + j])
            j += 1
    return unpack_star


# -- deletion targets ----------------------------------------------------------------------

def del_target(comp: Compiler, t: Expression) -> StmtFn:
    """Compile the target of a `del` statement into a statement closure."""
    if type(t) is Name:
        return del_name(comp, t.id)
    if type(t) is Attribute:
        return make_del_attr(comp.expr(t.value), t.attr)
    if type(t) is Subscript:
        oc: ExprFn = comp.expr(t.value)
        ic: ExprFn = comp.expr(t.index)
        return make_del_item(oc, ic)
    if type(t) is Tuple or type(t) is List:
        return make_del_all([del_target(comp, e) for e in t.elts])
    raise SyntaxError(f'cannot delete {type(t).__name__}')


def make_del_attr(oc: ExprFn, name: str) -> StmtFn:
    """`del obj.name`."""
    def del_attr(fr: Frame) -> None:
        delattr_any(oc(fr), name)
    return del_attr


def make_del_item(oc: ExprFn, ic: ExprFn) -> StmtFn:
    """`del obj[key]`."""
    def del_item(fr: Frame) -> None:
        o: Any = oc(fr)
        del o[ic(fr)]
    return del_item


def make_del_all(ds: list[StmtFn]) -> StmtFn:
    """`del a, b, ...`: delete each target in turn."""
    def del_all(fr: Frame) -> None:
        for d in ds:
            d(fr)
    return del_all
