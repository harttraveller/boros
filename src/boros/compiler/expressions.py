"""Compilation of attribute access, subscripts, displays and f-strings.

Every compile function here takes the Compiler and one syntax node and
returns a closure `f(fr)` that evaluates the node in frame `fr`.

The compile functions pick among several closure variants, each built by a
small factory (`make_...`).  The variants specialise on facts known at
compile time, such as "the object is a parameter of the current function"
or "the index is a constant", so the closure that runs does as little work
as possible: fetching a parameter straight from the frame saves a call to
a separate load closure, and the attribute variants inline the common case
of reading an attribute stored on an interpreted instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NoReturn

from ..lexer import syntax_error
from ..runtime.attributes import getattr_any, inst_getattr
from ..runtime.errors import unbound_free, unbound_local
from ..runtime.exceptions import SPECIAL_ATTRS, getattr_special
from ..runtime.lookup import K_MISSING, K_SLOT, has_special
from ..runtime.objects import Instance
from ..runtime.typechecks import type_name
from ..syntax import Const, Slice, Starred
from .names import compile_const, store_name

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core_types import ExprFn, Frame, StoreFn
    from ..runtime.objects import Signal
    from ..syntax import (
        Attribute,
        Await,
        DictDisplay,
        Expression,
        FormattedValue,
        IfExp,
        JoinedStr,
        List,
        NamedExpr,
        SetDisplay,
        Subscript,
        Tuple,
        Yield,
        YieldFrom,
    )
    from .compiler import Compiler


# -- attribute access ------------------------------------------------------------
#
# Reading `o.name` on an interpreted Instance consults the class's attribute
# cache (`cls.acache`), which maps a name to an entry (kind, value, owner)
# describing what the class's MRO holds under that name.  When the class has
# nothing (K_MISSING) the value can only come from the instance dict, and a
# __slots__ entry (K_SLOT) means it comes from the slot values; both are
# answered inline.  Everything else (methods, properties, descriptors, a
# cache miss) goes through the general inst_getattr.  Non-instances use
# getattr_any.  The three variants below differ only in how they fetch `o`.

def compile_attribute(comp: Compiler, n: Attribute) -> ExprFn:
    """Compile `value.attr`."""
    name: str = n.attr
    if name in SPECIAL_ATTRS:
        return make_attr_special(comp.expr(n.value), name)
    oname: str | None = comp.local_name(n.value)
    if oname is None:
        return make_attr(comp.expr(n.value), name)
    if comp.is_param(oname):
        return make_attr_param(oname, name)
    return make_attr_local(oname, name)


def make_attr_param(oname: str, name: str) -> ExprFn:
    """`p.name` where p is a parameter, which is always bound."""

    def attr_param(fr: Frame) -> Any:
        o: Any = fr[oname]
        if type(o) is Instance:
            e: tuple[Signal, Any, Any] | None = o.cls.acache.get(name)
            if e is not None:
                k: Signal = e[0]
                if k is K_MISSING:
                    d: dict[str, Any] = o.d
                    if name in d:
                        return d[name]
                elif k is K_SLOT:
                    sv: dict[str, Any] | None = o.sv
                    if sv is not None and name in sv:
                        return sv[name]
            return inst_getattr(o, name)
        return getattr_any(o, name)
    return attr_param


def make_attr_local(oname: str, name: str) -> ExprFn:
    """`v.name` where v is a local variable, which may be unbound."""

    def attr_local(fr: Frame) -> Any:
        try:
            o: Any = fr[oname]
        except KeyError:
            raise unbound_local(oname) from None
        if type(o) is Instance:
            e: tuple[Signal, Any, Any] | None = o.cls.acache.get(name)
            if e is not None:
                k: Signal = e[0]
                if k is K_MISSING:
                    d: dict[str, Any] = o.d
                    if name in d:
                        return d[name]
                elif k is K_SLOT:
                    sv: dict[str, Any] | None = o.sv
                    if sv is not None and name in sv:
                        return sv[name]
            return inst_getattr(o, name)
        return getattr_any(o, name)
    return attr_local


def make_attr(oc: ExprFn, name: str) -> ExprFn:
    """`expr.name` for an arbitrary object expression."""

    def attr(fr: Frame) -> Any:
        o: Any = oc(fr)
        if type(o) is Instance:
            e: tuple[Signal, Any, Any] | None = o.cls.acache.get(name)
            if e is not None:
                k: Signal = e[0]
                if k is K_MISSING:
                    d: dict[str, Any] = o.d
                    if name in d:
                        return d[name]
                elif k is K_SLOT:
                    sv: dict[str, Any] | None = o.sv
                    if sv is not None and name in sv:
                        return sv[name]
            return inst_getattr(o, name)
        return getattr_any(o, name)
    return attr


def make_attr_special(oc: ExprFn, name: str) -> ExprFn:
    """`expr.name` for a name in SPECIAL_ATTRS, such as `e.__context__` or
    `sys.exc_info`, whose value from a host object may need mapping to an
    interpreted exception."""

    def attr_special(fr: Frame) -> Any:
        return getattr_special(oc(fr), name)
    return attr_special


# -- subscripts ------------------------------------------------------------------

def compile_subscript(comp: Compiler, n: Subscript) -> ExprFn:
    """Compile `value[index]`, including slices such as `value[lo:hi]`."""
    oc: ExprFn = comp.expr(n.value)
    idx: Expression = n.index
    if type(idx) is Slice:
        return compile_slice_subscript(comp, oc, idx)
    oname: str | None = comp.local_name(n.value)
    if oname is not None:
        ok: str = 'param' if comp.is_param(oname) else 'local'
        kk, kname = comp.operand(idx)
        f: ExprFn | None = subscript_inline(comp, ok, oname, kk, kname)
        if f is not None:
            return f
    if type(idx) is Const:
        return make_subscript_const(oc, idx.value)
    return make_subscript(oc, comp.expr(idx))


def make_subscript_const(oc: ExprFn, c: Any) -> ExprFn:
    """`expr[constant]`."""

    def subscript_c(fr: Frame) -> Any:
        return oc(fr)[c]
    return subscript_c


def make_subscript(oc: ExprFn, ic: ExprFn) -> ExprFn:
    """`expr[expr]`: the general case."""

    def subscript(fr: Frame) -> Any:
        o: Any = oc(fr)
        return o[ic(fr)]
    return subscript


def compile_slice_subscript(comp: Compiler, oc: ExprFn, idx: Slice) -> ExprFn:
    """`o[lo:hi]` and friends.  Without a step, the closure indexes the
    object with host slice syntax directly; with a step, it indexes it with
    a slice object built by compile_slice."""
    lower: Expression | None = idx.lower
    upper: Expression | None = idx.upper
    if idx.step is not None:
        return make_slice_step(oc, comp.expr(idx))
    if lower is None:
        if upper is None:
            return make_slice_all(oc)
        return make_slice_hi(oc, comp.expr(upper))
    lo: ExprFn = comp.expr(lower)
    if upper is None:
        return make_slice_lo(oc, lo)
    return make_slice_lohi(oc, lo, comp.expr(upper))


def make_slice_all(oc: ExprFn) -> ExprFn:
    """`o[:]`."""

    def slice_all(fr: Frame) -> Any:
        return oc(fr)[:]
    return slice_all


def make_slice_hi(oc: ExprFn, hi: ExprFn) -> ExprFn:
    """`o[:hi]`."""

    def slice_hi(fr: Frame) -> Any:
        return oc(fr)[:hi(fr)]
    return slice_hi


def make_slice_lo(oc: ExprFn, lo: ExprFn) -> ExprFn:
    """`o[lo:]`."""

    def slice_lo(fr: Frame) -> Any:
        return oc(fr)[lo(fr):]
    return slice_lo


def make_slice_lohi(oc: ExprFn, lo: ExprFn, hi: ExprFn) -> ExprFn:
    """`o[lo:hi]`."""

    def slice_lohi(fr: Frame) -> Any:
        o: Any = oc(fr)
        return o[lo(fr):hi(fr)]
    return slice_lohi


def make_slice_step(oc: ExprFn, sc: ExprFn) -> ExprFn:
    """`o[lo:hi:step]`, where sc builds the slice object."""

    def slice_step(fr: Frame) -> Any:
        o: Any = oc(fr)
        return o[sc(fr)]
    return slice_step


def subscript_inline(comp: Compiler, ok: str, oname: str, kk: str | None, k: Any) -> ExprFn | None:
    """A closure for `o[key]` that fetches both operands straight from the
    frame, or None if this combination has no inlined variant.

    ok is 'param' or 'local' (the kind of the name `oname` holding the
    object); kk is the operand kind of the key (see Compiler.operand) and k
    its name or constant value."""
    if kk is None:
        return None
    if ok == 'param':
        factory: Callable[[str, Any], ExprFn] | None = PARAM_SUBSCRIPTS.get(kk)
    else:
        factory = LOCAL_SUBSCRIPTS.get(kk)
    if factory is None:
        return None
    return factory(oname, k)


def make_sub_pc(oname: str, k: Any) -> ExprFn:
    """`param[constant]`."""

    def sub_pc(fr: Frame) -> Any:
        return fr[oname][k]
    return sub_pc


def make_sub_pf(oname: str, k: str) -> ExprFn:
    """`param[free variable of the enclosing function]`."""

    def sub_pf(fr: Frame) -> Any:
        try:
            key: Any = fr['.up'][k]
        except KeyError:
            raise unbound_free(k) from None
        return fr[oname][key]
    return sub_pf


def make_sub_pp(oname: str, k: str) -> ExprFn:
    """`param[param]`."""

    def sub_pp(fr: Frame) -> Any:
        return fr[oname][fr[k]]
    return sub_pp


def make_sub_pl(oname: str, k: str) -> ExprFn:
    """`param[local]`."""

    def sub_pl(fr: Frame) -> Any:
        o: Any = fr[oname]
        try:
            key: Any = fr[k]
        except KeyError:
            raise unbound_local(k) from None
        return o[key]
    return sub_pl


def make_sub_lc(oname: str, k: Any) -> ExprFn:
    """`local[constant]`."""

    def sub_lc(fr: Frame) -> Any:
        try:
            o: Any = fr[oname]
        except KeyError:
            raise unbound_local(oname) from None
        return o[k]
    return sub_lc


def make_sub_lf(oname: str, k: str) -> ExprFn:
    """`local[free variable of the enclosing function]`."""

    def sub_lf(fr: Frame) -> Any:
        try:
            o: Any = fr[oname]
        except KeyError:
            raise unbound_local(oname) from None
        try:
            key: Any = fr['.up'][k]
        except KeyError:
            raise unbound_free(k) from None
        return o[key]
    return sub_lf


# Inlined subscript variants by key kind, for a parameter or a local object.
PARAM_SUBSCRIPTS: dict[str, Callable[[str, Any], ExprFn]] = {
    'const': make_sub_pc, 'free1': make_sub_pf, 'param': make_sub_pp, 'local': make_sub_pl,
}

LOCAL_SUBSCRIPTS: dict[str, Callable[[str, Any], ExprFn]] = {'const': make_sub_lc, 'free1': make_sub_lf}


def compile_slice(comp: Compiler, n: Slice) -> ExprFn:
    """Compile a slice `lo:hi:step` into a closure building a slice object."""
    lo: ExprFn | None = comp.expr(n.lower) if n.lower is not None else None
    hi: ExprFn | None = comp.expr(n.upper) if n.upper is not None else None
    st: ExprFn | None = comp.expr(n.step) if n.step is not None else None

    def make_slice(fr: Frame) -> slice:
        return slice(lo(fr) if lo is not None else None,
                     hi(fr) if hi is not None else None,
                     st(fr) if st is not None else None)
    return make_slice


# -- displays: tuples, lists, sets, dicts -------------------------------------------

def sequence_items(comp: Compiler, elts: list[Expression]) -> tuple[bool, list[tuple[bool, ExprFn]]]:
    """Compile the elements of a display (or the positional arguments of a
    call).  Returns (has_star, items) where items pairs each element's
    closure with whether it was `*starred` (its value is to be unpacked)."""
    items: list[tuple[bool, ExprFn]] = []
    has_star: bool = False
    for e in elts:
        if type(e) is Starred:
            has_star = True
            items.append((True, comp.expr(e.value)))
        else:
            items.append((False, comp.expr(e)))
    return has_star, items


def extend_star(out: list[Any], v: Any) -> None:
    """out.extend(v) for `*v` in a list or tuple display, which, unlike a
    set display, words the error for a v that is not iterable as Python
    does."""
    try:
        out.extend(v)
    except TypeError:
        if is_iterable(v):
            raise
        raise TypeError(f'Value after * must be an iterable, not {type_name(v)}') from None


def is_iterable(v: Any) -> bool:
    """Whether v supports iteration (__iter__) or the sequence protocol
    (__getitem__), the test Python makes before blaming v itself."""
    if type(v) is Instance:
        return has_special(v, '__iter__') or has_special(v, '__getitem__')
    t: type = type(v)
    return hasattr(t, '__iter__') or hasattr(t, '__getitem__')


def build_list(comp: Compiler, items: list[tuple[bool, ExprFn]],
               extend: Callable[[list[Any], Any], None] = extend_star) -> ExprFn:
    """A closure building a list from sequence_items, unpacking starred
    items with extend(out, value) (extend_star for list and tuple displays,
    list.extend for set displays)."""

    def build(fr: Frame) -> list[Any]:
        out: list[Any] = []
        for star, c in items:
            if star:
                extend(out, c(fr))
            else:
                out.append(c(fr))
        return out
    return build


def compile_tuple(comp: Compiler, n: Tuple) -> ExprFn:
    """Compile a tuple display `(a, b, *c)`."""
    has_star, items = sequence_items(comp, n.elts)
    if has_star:
        return make_tuple_star(build_list(comp, items))
    cs: list[ExprFn] = [c for _, c in items]
    if len(cs) == 0:
        return compile_const(comp, Const(n.line, ()))
    if len(cs) == 2:
        return make_tuple2(cs[0], cs[1])
    return make_tuple(cs)


def make_tuple_star(build: ExprFn) -> ExprFn:
    """A tuple display with starred items."""

    def tuple_star(fr: Frame) -> tuple[Any, ...]:
        return tuple(build(fr))
    return tuple_star


def make_tuple2(a: ExprFn, b: ExprFn) -> ExprFn:
    """A pair `(a, b)`, the most common tuple display."""

    def tuple2(fr: Frame) -> tuple[Any, Any]:
        return (a(fr), b(fr))
    return tuple2


def make_tuple(cs: list[ExprFn]) -> ExprFn:
    """A tuple display without starred items."""

    def tuple_(fr: Frame) -> tuple[Any, ...]:
        return tuple([c(fr) for c in cs])
    return tuple_


def compile_list(comp: Compiler, n: List) -> ExprFn:
    """Compile a list display `[a, b, *c]`."""
    has_star, items = sequence_items(comp, n.elts)
    if has_star:
        return build_list(comp, items)
    cs: list[ExprFn] = [c for _, c in items]

    def list_(fr: Frame) -> list[Any]:
        return [c(fr) for c in cs]
    return list_


def compile_set(comp: Compiler, n: SetDisplay) -> ExprFn:
    """Compile a set display `{a, b, *c}`."""
    _, items = sequence_items(comp, n.elts)
    build: ExprFn = build_list(comp, items, list.extend)

    def set_(fr: Frame) -> set[Any]:
        return set(build(fr))
    return set_


def compile_dict(comp: Compiler, n: DictDisplay) -> ExprFn:
    """Compile a dict display `{k: v, **m}`.  Small displays without `**`
    (such as the frames built by the interpreter's own call fast paths) get
    closures without a loop; a `**m` entry copies the keys of any mapping,
    using its keys() method as Python does."""
    if None not in n.keys and 1 <= len(n.keys) <= 2:
        return small_dict(comp, n)
    items: list[tuple[ExprFn | None, ExprFn]] = []
    for k, v in zip(n.keys, n.values):
        items.append((comp.expr(k) if k is not None else None, comp.expr(v)))
    return make_dict_display(items)


def small_dict(comp: Compiler, n: DictDisplay) -> ExprFn:
    """A dict display with one or two `key: value` items."""
    kcs: list[ExprFn] = []
    for k in n.keys:
        assert k is not None
        kcs.append(comp.expr(k))
    vcs: list[ExprFn] = [comp.expr(v) for v in n.values]
    if len(kcs) == 1:
        return make_dict1(kcs[0], vcs[0])
    last: Expression | None = n.keys[1]
    if type(last) is Const:
        return make_dict2_const_key(kcs[0], vcs[0], last.value, vcs[1])
    return make_dict2(kcs[0], vcs[0], kcs[1], vcs[1])


def make_dict1(kc: ExprFn, vc: ExprFn) -> ExprFn:
    """`{k: v}`."""
    def dict1(fr: Frame) -> dict[Any, Any]:
        return {kc(fr): vc(fr)}
    return dict1


def make_dict2(kc0: ExprFn, vc0: ExprFn, kc1: ExprFn, vc1: ExprFn) -> ExprFn:
    """`{k0: v0, k1: v1}`."""
    def dict2(fr: Frame) -> dict[Any, Any]:
        return {kc0(fr): vc0(fr), kc1(fr): vc1(fr)}
    return dict2


def make_dict2_const_key(kc0: ExprFn, vc0: ExprFn, k1: Any, vc1: ExprFn) -> ExprFn:
    """`{k0: v0, 'constant': v1}`."""
    def dict2c(fr: Frame) -> dict[Any, Any]:
        return {kc0(fr): vc0(fr), k1: vc1(fr)}
    return dict2c


def make_dict_display(items: list[tuple[ExprFn | None, ExprFn]]) -> ExprFn:
    """The general dict display, with `**mapping` entries."""
    def dict_(fr: Frame) -> dict[Any, Any]:
        d: dict[Any, Any] = {}
        for kc, vc in items:
            if kc is None:
                merge_mapping(d, vc(fr))
            else:
                k: Any = kc(fr)
                d[k] = vc(fr)
        return d
    return dict_


def merge_mapping(d: dict[Any, Any], m: Any) -> None:
    """Copy the items of mapping m into d (a `**m` display entry)."""
    if type(m) is dict:
        d.update(m)
        return
    try:
        keys: Any = m.keys()
    except AttributeError:
        raise TypeError(f"'{type_name(m)}' object is not a mapping") from None
    for k in keys:
        d[k] = m[k]


# -- other expressions ---------------------------------------------------------------

def compile_ifexp(comp: Compiler, n: IfExp) -> ExprFn:
    """Compile a conditional expression `body if test else orelse`."""
    tc: ExprFn = comp.expr(n.test)
    bc: ExprFn = comp.expr(n.body)
    oc: ExprFn = comp.expr(n.orelse)

    def ifexp(fr: Frame) -> Any:
        if tc(fr):
            return bc(fr)
        return oc(fr)
    return ifexp


def compile_namedexpr(comp: Compiler, n: NamedExpr) -> ExprFn:
    """Compile an assignment expression `target := value`."""
    vc: ExprFn = comp.expr(n.value)
    store: StoreFn = store_name(comp, n.target.id)

    def namedexpr(fr: Frame) -> Any:
        v: Any = vc(fr)
        store(fr, v)
        return v
    return namedexpr


def compile_joinedstr(comp: Compiler, n: JoinedStr) -> ExprFn:
    """Compile an f-string: the parts are string constants and formatted
    values, each evaluating to a string, joined together."""
    cs: list[ExprFn] = [comp.expr(v) for v in n.values]
    if len(cs) == 0:
        return compile_const(comp, Const(n.line, ''))
    if len(cs) == 1:
        c0: ExprFn = cs[0]
        if type(n.values[0]) is Const:
            return c0

        def joined1(fr: Frame) -> Any:
            return c0(fr)
        return joined1

    def joined(fr: Frame) -> str:
        return ''.join([c(fr) for c in cs])
    return joined


def compile_formattedvalue(comp: Compiler, n: FormattedValue) -> ExprFn:
    """Compile an f-string replacement field `{value!conv:spec}`: apply the
    conversion (repr, str or ascii), then format() with the spec, which is
    itself an f-string."""
    vc: ExprFn = comp.expr(n.value)
    conv: str | None = n.conv
    sc: ExprFn | None = comp.expr(n.spec) if n.spec is not None else None
    if conv is None and sc is None:
        return make_format_plain(vc)

    def fmt_full(fr: Frame) -> str:
        v: Any = vc(fr)
        if conv == 'r':
            v = repr(v)
        elif conv == 's':
            v = str(v)
        elif conv == 'a':
            v = ascii(v)
        if sc is None:
            return format(v, '')
        return format(v, sc(fr))
    return fmt_full


def make_format_plain(vc: ExprFn) -> ExprFn:
    """`{value}` with no conversion and no format spec."""

    def fmt(fr: Frame) -> str:
        v: Any = vc(fr)
        if type(v) is str:
            return v
        return format(v, '')
    return fmt


def compile_starred(comp: Compiler, n: Starred) -> NoReturn:
    """A starred expression outside a display, call or assignment target."""
    raise syntax_error("can't use starred expression here", comp.filename, n.line)


def compile_yield(comp: Compiler, n: Yield | YieldFrom) -> NoReturn:
    """`yield` reaching the ordinary compiler: it is outside any function
    (functions containing yield are compiled by the generator compiler)."""
    raise syntax_error("'yield' outside function", comp.filename, n.line)


def compile_await(comp: Compiler, n: Await) -> NoReturn:
    """`await` reaching the ordinary compiler: it is outside any async function."""
    raise syntax_error("'await' outside function", comp.filename, n.line)
