"""Compilation of the `match` statement.

Each case pattern compiles to a matcher `m(fr, subject) -> bool` that tests
the subject and, if the whole pattern matches, binds the pattern's capture
names in the frame.  Inside it every sub-pattern is a matcher
`m(fr, value, binds) -> bool` that appends the captures it makes to `binds`
as (store, value) pairs instead of storing them, so that, as in CPython, a
pattern that fails part-way binds nothing.  The match statement tries its
cases in order and runs the body of the first case whose pattern matches
and whose guard (if any) is true; the names are bound before the guard runs.
"""

from __future__ import annotations

import collections.abc
from typing import TYPE_CHECKING, Any

from ..runtime.attributes import getattr_any
from ..runtime.calls import call
from ..runtime.objects import MISSING, Class, Instance
from ..runtime.typechecks import b_isinstance, type_name
from ..syntax import PAs, PCapture, PClass, PMapping, POr, PSequence, PSingleton, PStar, PValue, PWildcard
from .names import store_name
from .statements import block

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core_types import ExprFn, Frame, StmtFn, StoreFn
    from ..runtime.objects import Signal
    from ..syntax import Match, Pattern
    from .compiler import Compiler

    PatternFn = Callable[[Frame, Any], bool]
    """A compiled case pattern: matches a subject, binding names in the frame."""

    Binds = list[tuple[StoreFn, Any]]
    """The captures of a pattern being matched, stored once it has matched."""

    MatcherFn = Callable[[Frame, Any, Binds], bool]
    """A compiled sub-pattern: matches a value, adding its captures to binds."""


def is_match_sequence(v: Any) -> bool:
    """Can a sequence pattern match v?  Any sequence except the string
    types and dicts qualifies, including an instance of an interpreted
    subclass of one."""
    t: type = type(v)
    if t is list or t is tuple or t is range:
        return True
    if t is str or t is bytes or t is bytearray or t is dict:
        return False
    if t is Instance:
        return is_sequence_type(v.cls.native)
    return isinstance(v, collections.abc.Sequence)


def is_sequence_type(t: type | None) -> bool:
    """Whether (the host base class) t is a sequence other than a string type."""
    return t is not None and issubclass(t, collections.abc.Sequence) and not issubclass(t, (str, bytes, bytearray))


def is_match_mapping(v: Any) -> bool:
    """Can a mapping pattern match v (possibly an instance of an
    interpreted subclass of a mapping)?"""
    if type(v) is dict:
        return True
    if type(v) is Instance:
        t: type | None = v.cls.native
        return t is not None and issubclass(t, collections.abc.Mapping)
    return isinstance(v, collections.abc.Mapping)


# Builtin types whose class pattern `C(p)` matches p against the subject
# itself; their subclasses inherit the rule (unless they set __match_args__).
SELF_MATCHING: tuple[type, ...] = (bool, bytearray, bytes, dict, float, frozenset, int, list, set, str, tuple)


def compile_match(comp: Compiler, s: Match) -> StmtFn:
    """`match subject: case pattern if guard: body ...`."""
    sc: ExprFn = comp.expr(s.subject)
    cases: list[tuple[PatternFn, ExprFn | None, StmtFn]] = []
    for case in s.cases:
        m: PatternFn = pattern(comp, case.pattern)
        guard: ExprFn | None = comp.expr(case.guard) if case.guard is not None else None
        cases.append((m, guard, block(comp, case.body)))

    def match(fr: Frame) -> Signal | None:
        subject: Any = sc(fr)
        for m, guard, body in cases:
            if m(fr, subject) and (guard is None or guard(fr)):
                return body(fr)
        return None
    return match


def pattern(comp: Compiler, p: Pattern) -> PatternFn:
    """Compile the pattern of a case into a matcher that binds the names it
    captures only if the whole pattern matches."""
    m: MatcherFn = matcher(comp, p)

    def match_case(fr: Frame, v: Any) -> bool:
        binds: Binds = []
        if m(fr, v, binds):
            for store, x in binds:
                store(fr, x)
            return True
        return False
    return match_case


def matcher(comp: Compiler, p: Pattern) -> MatcherFn:
    """Compile a pattern into a sub-pattern matcher."""
    compile_pattern: Callable[[Compiler, Any], MatcherFn] | None = PATTERN_COMPILERS.get(type(p))
    if compile_pattern is None:
        raise SyntaxError('bad pattern')
    return compile_pattern(comp, p)


# -- simple patterns ---------------------------------------------------------------------


def wildcard_pattern(comp: Compiler, p: PWildcard) -> MatcherFn:
    """`_` matches anything."""
    def match_any(fr: Frame, v: Any, binds: Binds) -> bool:
        return True
    return match_any


def capture_pattern(comp: Compiler, p: PCapture) -> MatcherFn:
    """`name` matches anything and binds it to name."""
    store: StoreFn = store_name(comp, p.name)

    def capture(fr: Frame, v: Any, binds: Binds) -> bool:
        binds.append((store, v))
        return True
    return capture


def value_pattern(comp: Compiler, p: PValue) -> MatcherFn:
    """A literal or dotted name matches subjects equal to its value."""
    vc: ExprFn = comp.expr(p.value)

    def match_value(fr: Frame, v: Any, binds: Binds) -> bool:
        return v == vc(fr)
    return match_value


def singleton_pattern(comp: Compiler, p: PSingleton) -> MatcherFn:
    """`None`, `True` and `False` match by identity."""
    c: bool | None = p.value

    def match_singleton(fr: Frame, v: Any, binds: Binds) -> bool:
        return v is c
    return match_singleton


def as_pattern(comp: Compiler, p: PAs) -> MatcherFn:
    """`pattern as name` binds the subject to name if pattern matches."""
    inner: MatcherFn = matcher(comp, p.pattern)
    store: StoreFn = store_name(comp, p.name)

    def as_(fr: Frame, v: Any, binds: Binds) -> bool:
        if inner(fr, v, binds):
            binds.append((store, v))
            return True
        return False
    return as_


def or_pattern(comp: Compiler, p: POr) -> MatcherFn:
    """`p1 | p2 | ...` tries the alternatives from left to right, dropping
    the captures of each one that fails."""
    alts: list[MatcherFn] = [matcher(comp, x) for x in p.patterns]

    def or_(fr: Frame, v: Any, binds: Binds) -> bool:
        n: int = len(binds)
        for a in alts:
            if a(fr, v, binds):
                return True
            del binds[n:]
        return False
    return or_


# -- sequence patterns -------------------------------------------------------------------


def sequence_pattern(comp: Compiler, p: PSequence) -> MatcherFn:
    """`[p1, p2, *rest, p3]`: the subject must be a sequence (see
    is_match_sequence) of the right length whose items match the
    sub-patterns; a star sub-pattern takes the items left over in the
    middle, as a list."""
    pats: list[Pattern] = p.patterns
    star: int = -1
    star_name: str | None = None
    for i, x in enumerate(pats):
        if type(x) is PStar:
            star = i
            star_name = x.name
    if star < 0:
        return make_fixed_sequence([matcher(comp, x) for x in pats])
    before: list[MatcherFn] = [sequence_item(comp, x) for x in pats[:star]]
    rest: StoreFn | None = store_name(comp, star_name) if star_name is not None else None
    after: list[MatcherFn] = [matcher(comp, x) for x in pats[star + 1:]]
    return make_star_sequence(before, rest, after)


def sequence_item(comp: Compiler, x: Pattern) -> MatcherFn:
    """Compile a sub-pattern that comes before the star of a sequence pattern.

    That is an ordinary pattern unless the sequence pattern has several
    stars, which CPython rejects at compile time.  boros accepts them: only
    the last star collects items, and an earlier `*name` captures its item
    and then fails to match."""
    if type(x) is not PStar:
        return matcher(comp, x)
    if x.name is None:
        def no_matcher(fr: Frame, v: Any, binds: Binds) -> bool:
            raise TypeError("'NoneType' object is not callable")
        return no_matcher
    store: StoreFn = store_name(comp, x.name)

    def store_and_fail(fr: Frame, v: Any, binds: Binds) -> bool:
        binds.append((store, v))
        return False
    return store_and_fail


def make_fixed_sequence(subs: list[MatcherFn]) -> MatcherFn:
    """A sequence pattern without a star: the lengths must be equal."""
    n: int = len(subs)

    def seq(fr: Frame, v: Any, binds: Binds) -> bool:
        if not is_match_sequence(v):
            return False
        items: list[Any] = list(v)
        if len(items) != n:
            return False
        i: int = 0
        while i < n:
            if not subs[i](fr, items[i], binds):
                return False
            i += 1
        return True
    return seq


def make_star_sequence(before: list[MatcherFn], rest: StoreFn | None, after: list[MatcherFn]) -> MatcherFn:
    """A sequence pattern with a star: the sub-patterns before it match the
    first items, those after it the last items, and rest (None for `*_`)
    receives the list of items in between."""
    nbefore: int = len(before)
    nafter: int = len(after)
    need: int = nbefore + nafter

    def seq_star(fr: Frame, v: Any, binds: Binds) -> bool:
        if not is_match_sequence(v):
            return False
        items: list[Any] = list(v)
        m: int = len(items)
        if m < need:
            return False
        i: int = 0
        while i < nbefore:
            if not before[i](fr, items[i], binds):
                return False
            i += 1
        j: int = 0
        while j < nafter:
            if not after[j](fr, items[m - nafter + j], binds):
                return False
            j += 1
        if rest is not None:
            binds.append((rest, items[nbefore:m - nafter]))
        return True
    return seq_star


# -- mapping and class patterns ----------------------------------------------------------


def mapping_pattern(comp: Compiler, p: PMapping) -> MatcherFn:
    """`{key: p, ..., **rest}`: the subject must be a mapping with at least
    as many items as there are keys and containing every key, whose values
    match the sub-patterns; rest receives a dict of the remaining items."""
    keys: list[ExprFn] = [comp.expr(k) for k in p.keys]
    subs: list[MatcherFn] = [matcher(comp, x) for x in p.patterns]
    rest: StoreFn | None = store_name(comp, p.rest) if p.rest is not None else None
    nkeys: int = len(keys)

    def mapping(fr: Frame, v: Any, binds: Binds) -> bool:
        if not is_match_mapping(v) or len(v) < nkeys:
            return False
        ks: list[Any] = [kc(fr) for kc in keys]
        values: list[Any] | None = mapping_values(v, ks)
        if values is None:
            return False
        for sub, x in zip(subs, values):
            if not sub(fr, x, binds):
                return False
        if rest is not None:
            d: dict[Any, Any] = dict(v)
            for k in ks:
                del d[k]
            binds.append((rest, d))
        return True
    return mapping


def mapping_values(v: Any, keys: list[Any]) -> list[Any] | None:
    """The values of `keys` in mapping v, or None if one is missing.  As in
    CPython they are looked up with v.get() (so a dict subclass's
    __getitem__ and __missing__ are not used), and a key that occurs twice
    is an error."""
    get: Any = v.get if type(v) is dict else getattr_any(v, 'get')
    seen: set[Any] = set()
    values: list[Any] = []
    for k in keys:
        if k in seen:
            raise ValueError(f'mapping pattern checks duplicate key ({k!r})')
        seen.add(k)
        x: Any = call(get, (k, MISSING), None)
        if x is MISSING:
            return None
        values.append(x)
    return values


def class_pattern(comp: Compiler, p: PClass) -> MatcherFn:
    """`C(p1, p2, name=p3)`: the subject must be an instance of C; then the
    attributes the sub-patterns match are fetched (see class_attributes),
    and the sub-patterns are matched against them in order."""
    cc: ExprFn = comp.expr(p.cls)
    nsubs: int = len(p.patterns)
    kwd_names: list[str] = p.kwd_names
    subs: list[MatcherFn] = [matcher(comp, x) for x in p.patterns + p.kwd_patterns]

    def match_class(fr: Frame, v: Any, binds: Binds) -> bool:
        cls: Any = cc(fr)
        if type(cls) is not Class and not isinstance(cls, type):
            raise TypeError('called match pattern must be a class')
        if not b_isinstance(v, cls):
            return False
        attrs: list[Any] | None = class_attributes(cls, v, nsubs, kwd_names)
        if attrs is None:
            return False
        for sub, a in zip(subs, attrs):
            if not sub(fr, a, binds):
                return False
        return True
    return match_class


def class_attributes(cls: Any, v: Any, nsubs: int, kwd_names: list[str]) -> list[Any] | None:
    """The values the sub-patterns of class pattern `cls(...)` match, for
    subject v (an instance of cls): for nsubs positional sub-patterns the
    attributes named by cls.__match_args__ (or v itself, see
    positional_names), then the attributes kwd_names name.  None if v lacks
    one of them; the TypeErrors are CPython's."""
    attrs: list[Any] = []
    seen: list[str] = []
    if nsubs:
        names: list[Any] | None = positional_names(cls, nsubs)
        if names is None:
            attrs.append(v)
        else:
            for name in names:
                if type(name) is not str:
                    raise TypeError(f'__match_args__ elements must be strings (got {type_name(name)})')
                a: Any = match_attribute(cls, v, name, seen)
                if a is MISSING:
                    return None
                attrs.append(a)
    for name in kwd_names:
        a = match_attribute(cls, v, name, seen)
        if a is MISSING:
            return None
        attrs.append(a)
    return attrs


def positional_names(cls: Any, nsubs: int) -> list[Any] | None:
    """The attribute names that the nsubs positional sub-patterns of class
    pattern `cls(...)` match: the first items of cls.__match_args__.  None
    means that the single sub-pattern matches the subject itself, which is
    the rule for the builtin types in SELF_MATCHING and their subclasses
    that do not set __match_args__."""
    try:
        match_args: Any = getattr_any(cls, '__match_args__')
    except AttributeError:
        base: Any = cls.native if type(cls) is Class else cls
        match_self: bool = base is not None and issubclass(base, SELF_MATCHING)
        check_positional_count(cls, 1 if match_self else 0, nsubs)
        return None
    if type(match_args) is not tuple:
        raise TypeError(f'{cls.__name__}.__match_args__ must be a tuple (got {type_name(match_args)})')
    check_positional_count(cls, len(match_args), nsubs)
    return list(match_args[:nsubs])


def check_positional_count(cls: Any, allowed: int, nsubs: int) -> None:
    """The error for more positional sub-patterns than class cls allows."""
    if allowed < nsubs:
        plural: str = '' if allowed == 1 else 's'
        raise TypeError(f'{cls.__name__}() accepts {allowed} positional sub-pattern{plural} ({nsubs} given)')


def match_attribute(cls: Any, v: Any, name: str, seen: list[str]) -> Any:
    """Attribute `name` of subject v for a sub-pattern of class pattern
    `cls(...)`, or MISSING if v has none; `seen` lists the names already
    used by the pattern, which must not repeat."""
    if name in seen:
        raise TypeError(f'{cls.__name__}() got multiple sub-patterns for attribute {name!r}')
    seen.append(name)
    try:
        return getattr_any(v, name)
    except AttributeError:
        return MISSING


PATTERN_COMPILERS: dict[type, Callable[[Compiler, Any], MatcherFn]] = {
    PWildcard: wildcard_pattern, PCapture: capture_pattern, PValue: value_pattern, PSingleton: singleton_pattern,
    PAs: as_pattern, POr: or_pattern, PSequence: sequence_pattern, PMapping: mapping_pattern,
    PClass: class_pattern,
}
