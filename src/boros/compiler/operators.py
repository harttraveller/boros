"""Compilation of operators and comparisons.

Arithmetic and comparisons are the bread and butter of most programs, so
this module specializes them heavily.  The generic closure for `a OP b` is
`fn(left(fr), right(fr))` with `fn` from the operator module; the
specialized variants compute exactly the same thing with less work:

- by operator: `a + b` gets a closure that uses the `+` syntax directly,
  which is cheaper than calling operator.add;
- by operand shape (see `Compiler.operand`): a constant operand is captured
  in the closure instead of being produced by a child closure, and a local
  variable or parameter is read inline with `fr[name]`.

Each variant lives in its own small factory function `make_*(...)` that
returns the closure; the `compile_*` functions only decide which factory
to use, mostly by looking the operator up in a table of factories.
"""

from __future__ import annotations

import operator
from typing import TYPE_CHECKING, Any

from ..runtime.builtin_functions import builtins_of, global_fallback
from ..runtime.errors import unbound_free, unbound_local
from ..syntax import Const, Name

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core_types import ExprFn, Frame
    from ..syntax import BinOp, BoolOp, Compare, Expression, UnaryOp
    from .compiler import Compiler

    # Type aliases (only needed by the type checker).
    BinaryFn = Callable[[Any, Any], Any]
    """A host function implementing a binary operator, e.g. operator.add."""
    NameConstFactory = Callable[[str, Any], ExprFn]
    """Builds a closure for `variable OP constant` from (name, constant)."""
    ConstFactory = Callable[[ExprFn, Any], ExprFn]
    """Builds a closure for `expression OP constant` from (left closure, constant)."""
    PairFactory = Callable[[ExprFn, ExprFn], ExprFn]
    """Builds a closure for `expression OP expression` from two closures."""


BINOPS: dict[str, BinaryFn] = {
    '+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv,
    '//': operator.floordiv, '%': operator.mod, '**': operator.pow, '<<': operator.lshift,
    '>>': operator.rshift, '&': operator.and_, '^': operator.xor, '|': operator.or_,
    '@': operator.matmul,
}
"""The host function implementing each binary operator."""

INPLACE_OPS: dict[str, BinaryFn] = {
    '+': operator.iadd, '-': operator.isub, '*': operator.imul, '/': operator.itruediv,
    '//': operator.ifloordiv, '%': operator.imod, '**': operator.ipow, '<<': operator.ilshift,
    '>>': operator.irshift, '&': operator.iand, '^': operator.ixor, '|': operator.ior,
    '@': operator.imatmul,
}
"""The host function implementing each augmented assignment (`x += y` etc.)."""


def _in(a: Any, b: Any) -> bool:
    """`a in b` (operator.contains takes its arguments the other way round)."""
    return a in b


def _not_in(a: Any, b: Any) -> bool:
    """`a not in b`."""
    return a not in b


COMPARE_FUNCS: dict[str, BinaryFn] = {
    '<': operator.lt, '<=': operator.le, '>': operator.gt, '>=': operator.ge,
    '==': operator.eq, '!=': operator.ne, 'is': operator.is_, 'is not': operator.is_not,
    'in': _in, 'not in': _not_in,
}
"""The host function implementing each comparison operator."""


# -- binary operators ------------------------------------------------------------

def compile_binop(comp: Compiler, n: BinOp) -> ExprFn:
    """Compile `left OP right`.

    Picks the most specialized closure available: `local OP constant`,
    then `expression OP constant`, then `expression OP expression`, each
    with dedicated closures for the most common operators and a generic
    closure calling the operator's host function for the rest.
    """
    op: str = n.op
    lc: ExprFn = comp.expr(n.left)
    right: Expression = n.right
    if type(right) is Const:
        return binop_const(comp, op, n.left, lc, right.value)
    fused: ExprFn | None = binop_local_free(comp, op, n.left, right)
    if fused is not None:
        return fused
    rc: ExprFn = comp.expr(right)
    factory: PairFactory | None = PAIR_BINOPS.get(op)
    if factory is not None:
        return factory(lc, rc)
    return make_binop(BINOPS[op], lc, rc)


def binop_const(comp: Compiler, op: str, left: Expression, lc: ExprFn, c: Any) -> ExprFn:
    """Compile `left OP c` where the right operand is the constant c."""
    lname: str | None = comp.local_name(left)
    if lname is not None:
        local_factory: NameConstFactory | None = LOCAL_CONST_BINOPS.get(op)
        if local_factory is not None:
            return local_factory(lname, c)
    factory: ConstFactory | None = CONST_BINOPS.get(op)
    if factory is not None:
        return factory(lc, c)
    return make_binop_const(BINOPS[op], lc, c)


def binop_local_free(comp: Compiler, op: str, left: Expression, right: Expression) -> ExprFn | None:
    """Compile `local OP free` (a local variable and a variable of the
    enclosing function) into one closure that reads both inline, or return
    None when the expression has another shape.

    This is the shape of the interpreter's own operator closures (for
    example `v + c` in an `x + 1` closure), so when boros runs itself it
    saves two interpreted calls per operator at every level."""
    factory: Callable[[str, str], ExprFn] | None = LOCAL_FREE_BINOPS.get(op)
    if factory is None or type(right) is not Name:
        return None
    lname: str | None = comp.local_name(left)
    if lname is None or comp.operand(right)[0] != 'free1':
        return None
    return factory(lname, right.id)


def make_add_local_free(lname: str, fname: str) -> ExprFn:
    """`local + free`."""
    def add_lf(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        try:
            w: Any = fr['.up'][fname]
        except KeyError:
            raise unbound_free(fname) from None
        return v + w
    return add_lf


def make_sub_local_free(lname: str, fname: str) -> ExprFn:
    """`local - free`."""
    def sub_lf(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        try:
            w: Any = fr['.up'][fname]
        except KeyError:
            raise unbound_free(fname) from None
        return v - w
    return sub_lf


LOCAL_FREE_BINOPS: dict[str, Callable[[str, str], ExprFn]] = {
    '+': make_add_local_free,
    '-': make_sub_local_free,
}


# `local OP constant`: the local is read inline, with an unbound check.

def make_add_local_const(lname: str, c: Any) -> ExprFn:
    """`local + c`."""
    def add_lc(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        return v + c
    return add_lc


def make_sub_local_const(lname: str, c: Any) -> ExprFn:
    """`local - c`."""
    def sub_lc(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        return v - c
    return sub_lc


def make_mul_local_const(lname: str, c: Any) -> ExprFn:
    """`local * c`."""
    def mul_lc(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        return v * c
    return mul_lc


LOCAL_CONST_BINOPS: dict[str, NameConstFactory] = {
    '+': make_add_local_const, '-': make_sub_local_const, '*': make_mul_local_const,
}
"""Closure factories for `local OP constant`, by operator."""


# `expression OP constant`: the constant is captured in the closure.

def make_add_const(lc: ExprFn, c: Any) -> ExprFn:
    """`left + c`."""
    def add_c(fr: Frame) -> Any:
        return lc(fr) + c
    return add_c


def make_sub_const(lc: ExprFn, c: Any) -> ExprFn:
    """`left - c`."""
    def sub_c(fr: Frame) -> Any:
        return lc(fr) - c
    return sub_c


def make_mul_const(lc: ExprFn, c: Any) -> ExprFn:
    """`left * c`."""
    def mul_c(fr: Frame) -> Any:
        return lc(fr) * c
    return mul_c


def make_mod_const(lc: ExprFn, c: Any) -> ExprFn:
    """`left % c`."""
    def mod_c(fr: Frame) -> Any:
        return lc(fr) % c
    return mod_c


def make_floordiv_const(lc: ExprFn, c: Any) -> ExprFn:
    """`left // c`."""
    def floordiv_c(fr: Frame) -> Any:
        return lc(fr) // c
    return floordiv_c


def make_binop_const(fn: BinaryFn, lc: ExprFn, c: Any) -> ExprFn:
    """`left OP c` for any operator, via its host function fn."""
    def binop_c(fr: Frame) -> Any:
        return fn(lc(fr), c)
    return binop_c


CONST_BINOPS: dict[str, ConstFactory] = {
    '+': make_add_const, '-': make_sub_const, '*': make_mul_const,
    '%': make_mod_const, '//': make_floordiv_const,
}
"""Closure factories for `expression OP constant`, by operator."""


# `expression OP expression`

def make_add(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left + right`."""
    def add(fr: Frame) -> Any:
        return lc(fr) + rc(fr)
    return add


def make_sub(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left - right`."""
    def sub(fr: Frame) -> Any:
        return lc(fr) - rc(fr)
    return sub


def make_mul(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left * right`."""
    def mul(fr: Frame) -> Any:
        return lc(fr) * rc(fr)
    return mul


def make_mod(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left % right`."""
    def mod(fr: Frame) -> Any:
        return lc(fr) % rc(fr)
    return mod


def make_binop(fn: BinaryFn, lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left OP right` for any operator, via its host function fn."""
    def binop(fr: Frame) -> Any:
        return fn(lc(fr), rc(fr))
    return binop


PAIR_BINOPS: dict[str, PairFactory] = {
    '+': make_add, '-': make_sub, '*': make_mul, '%': make_mod,
}
"""Closure factories for `expression OP expression`, by operator."""


# -- unary operators ---------------------------------------------------------------

def compile_unaryop(comp: Compiler, n: UnaryOp) -> ExprFn:
    """Compile `not x`, `-x`, `+x` or `~x`."""
    c: ExprFn = comp.expr(n.operand)
    return UNARY_OPS[n.op](c)


def make_not(c: ExprFn) -> ExprFn:
    """`not operand`."""
    def not_(fr: Frame) -> Any:
        return not c(fr)
    return not_


def make_neg(c: ExprFn) -> ExprFn:
    """`-operand`."""
    def neg(fr: Frame) -> Any:
        return -c(fr)
    return neg


def make_pos(c: ExprFn) -> ExprFn:
    """`+operand`."""
    def pos(fr: Frame) -> Any:
        return +c(fr)
    return pos


def make_invert(c: ExprFn) -> ExprFn:
    """`~operand`."""
    def invert(fr: Frame) -> Any:
        return ~c(fr)
    return invert


UNARY_OPS: dict[str, Callable[[ExprFn], ExprFn]] = {
    'not': make_not, '-': make_neg, '+': make_pos, '~': make_invert,
}
"""Closure factories for the unary operators."""


# -- boolean operators ---------------------------------------------------------------

def compile_boolop(comp: Compiler, n: BoolOp) -> ExprFn:
    """Compile `a and b and ...` or `a or b or ...`.

    Evaluation stops at the first operand that decides the result, and the
    result is that operand's value (not necessarily a bool).  The common
    two-operand form gets its own closures without a loop.
    """
    cs: list[ExprFn] = [comp.expr(v) for v in n.values]
    if n.op == 'and':
        if len(cs) == 2:
            return make_and2(cs[0], cs[1])
        return make_and(cs[:-1], cs[-1])
    if len(cs) == 2:
        return make_or2(cs[0], cs[1])
    return make_or(cs[:-1], cs[-1])


def make_and2(a: ExprFn, b: ExprFn) -> ExprFn:
    """`a and b`."""
    def and2(fr: Frame) -> Any:
        v: Any = a(fr)
        if not v:
            return v
        return b(fr)
    return and2


def make_and(first: list[ExprFn], last: ExprFn) -> ExprFn:
    """`first[0] and first[1] and ... and last`."""
    def and_(fr: Frame) -> Any:
        for c in first:
            v: Any = c(fr)
            if not v:
                return v
        return last(fr)
    return and_


def make_or2(a: ExprFn, b: ExprFn) -> ExprFn:
    """`a or b`."""
    def or2(fr: Frame) -> Any:
        v: Any = a(fr)
        if v:
            return v
        return b(fr)
    return or2


def make_or(first: list[ExprFn], last: ExprFn) -> ExprFn:
    """`first[0] or first[1] or ... or last`."""
    def or_(fr: Frame) -> Any:
        for c in first:
            v: Any = c(fr)
            if v:
                return v
        return last(fr)
    return or_


# -- comparisons ---------------------------------------------------------------------

def compile_compare(comp: Compiler, n: Compare) -> ExprFn:
    """Compile a comparison: a single `left OP right`, or a chain such as
    `a < b <= c`, which means `a < b and b <= c` with b evaluated once."""
    lc: ExprFn = comp.expr(n.left)
    if len(n.ops) == 1:
        return compare_single(comp, n.left, n.ops[0], n.comparators[0], lc)
    cs: list[ExprFn] = [comp.expr(c) for c in n.comparators]
    fns: list[BinaryFn] = [COMPARE_FUNCS[o] for o in n.ops]
    return make_chain(lc, list(zip(fns, cs)))


def compare_single(comp: Compiler, left: Expression, op: str, right: Expression, lc: ExprFn) -> ExprFn:
    """Compile `left OP right` (one operator).

    A parameter or local variable compared with a constant (`x == 0`,
    `x is None`) or a global (`x is MISSING`) gets a closure that reads
    both operands inline; any expression compared with a constant using
    `is`, `is not` or `==` captures the constant.  Everything else gets a
    closure per operator that combines the two operand closures.
    """
    lk, lname = comp.operand(left)
    rk, rv = comp.operand(right)
    f: ExprFn | None = None
    if rk == 'const':
        f = compare_const(lk, lname, op, rv, lc)
    elif rk == 'global' and (op == 'is' or op == 'is not'):
        f = compare_is_global(comp, lk, lname, rv, op == 'is')
    if f is not None:
        return f
    rc: ExprFn = comp.expr(right)
    return PAIR_COMPARES[op](lc, rc)


def compare_const(lk: str | None, lname: Any, op: str, c: Any, lc: ExprFn) -> ExprFn | None:
    """Compile `left OP c` for a constant c, given the operand kind lk and
    name lname of the left side (see Compiler.operand), or return None when
    there is no specialized closure for it."""
    if lk == 'param':
        return compare_param_const(lname, op, c)
    if lk == 'local':
        f: ExprFn | None = compare_local_const(lname, op, c)
        if f is not None:
            return f
    factory: ConstFactory | None = CONST_COMPARES.get(op)
    if factory is None:
        return None
    return factory(lc, c)


def compare_param_const(lname: str, op: str, c: Any) -> ExprFn:
    """Compile `param OP c`; parameters are always bound, so they are read
    with a plain `fr[name]`."""
    factory: NameConstFactory | None = PARAM_CONST_COMPARES.get(op)
    if factory is not None:
        return factory(lname, c)
    return make_compare_param_const(COMPARE_FUNCS[op], lname, c)


def compare_local_const(lname: str, op: str, c: Any) -> ExprFn | None:
    """Compile `local OP c`, or return None for `in` / `not in`."""
    factory: NameConstFactory | None = LOCAL_CONST_COMPARES.get(op)
    if factory is not None:
        return factory(lname, c)
    if op in GENERIC_LOCAL_CONST_COMPARES:
        return make_compare_local_const(COMPARE_FUNCS[op], lname, c)
    return None


def compare_is_global(comp: Compiler, lk: str | None, lname: Any, gname: str, is_op: bool) -> ExprFn | None:
    """Compile `name is GLOBAL` / `name is not GLOBAL` for a parameter or
    local `name`, or return None for other left operands."""
    if lk == 'param':
        return make_is_param_global(comp.g, lname, gname, is_op)
    if lk == 'local':
        return make_is_local_global(comp.g, lname, gname, is_op)
    return None


# `param OP constant`

def make_is_param_const(lname: str, c: Any) -> ExprFn:
    """`param is c`."""
    def is_param_c(fr: Frame) -> Any:
        return fr[lname] is c
    return is_param_c


def make_is_not_param_const(lname: str, c: Any) -> ExprFn:
    """`param is not c`."""
    def is_not_param_c(fr: Frame) -> Any:
        return fr[lname] is not c
    return is_not_param_c


def make_eq_param_const(lname: str, c: Any) -> ExprFn:
    """`param == c`."""
    def eq_param_c(fr: Frame) -> Any:
        return fr[lname] == c
    return eq_param_c


def make_lt_param_const(lname: str, c: Any) -> ExprFn:
    """`param < c`."""
    def lt_param_c(fr: Frame) -> Any:
        return fr[lname] < c
    return lt_param_c


def make_compare_param_const(fn: BinaryFn, lname: str, c: Any) -> ExprFn:
    """`param OP c` for any comparison, via its host function fn."""
    def cmp_param_c(fr: Frame) -> Any:
        return fn(fr[lname], c)
    return cmp_param_c


PARAM_CONST_COMPARES: dict[str, NameConstFactory] = {
    'is': make_is_param_const, 'is not': make_is_not_param_const,
    '==': make_eq_param_const, '<': make_lt_param_const,
}
"""Closure factories for `param OP constant`, by operator."""


# `local OP constant`: the local is read inline, with an unbound check.

def make_is_local_const(lname: str, c: Any) -> ExprFn:
    """`local is c`."""
    def is_local_c(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        return v is c
    return is_local_c


def make_is_not_local_const(lname: str, c: Any) -> ExprFn:
    """`local is not c`."""
    def is_not_local_c(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        return v is not c
    return is_not_local_c


def make_lt_local_const(lname: str, c: Any) -> ExprFn:
    """`local < c`."""
    def lt_lc(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        return v < c
    return lt_lc


def make_eq_local_const(lname: str, c: Any) -> ExprFn:
    """`local == c`."""
    def eq_lc(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        return v == c
    return eq_lc


def make_compare_local_const(fn: BinaryFn, lname: str, c: Any) -> ExprFn:
    """`local OP c` for any comparison, via its host function fn."""
    def cmp_lc(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        return fn(v, c)
    return cmp_lc


LOCAL_CONST_COMPARES: dict[str, NameConstFactory] = {
    'is': make_is_local_const, 'is not': make_is_not_local_const,
    '<': make_lt_local_const, '==': make_eq_local_const,
}
"""Closure factories for `local OP constant`, by operator."""

GENERIC_LOCAL_CONST_COMPARES: tuple[str, ...] = ('>', '<=', '>=', '!=')
"""The other operators for which `local OP constant` reads the local inline
(through make_compare_local_const)."""


# `name is GLOBAL`: both variables are read inline.

def make_is_param_global(g: Frame, lname: str, gname: str, is_op: bool) -> ExprFn:
    """`param is GLOBAL` (is_op true) or `param is not GLOBAL`."""
    b: dict[str, Any] = builtins_of(g)

    def is_param_global(fr: Frame) -> Any:
        v: Any = fr[lname]
        if gname in g:
            w: Any = g[gname]
        elif gname in b:
            w = b[gname]
        else:
            w = global_fallback(gname, g, b)
        if is_op:
            return v is w
        return v is not w
    return is_param_global


def make_is_local_global(g: Frame, lname: str, gname: str, is_op: bool) -> ExprFn:
    """`local is GLOBAL` (is_op true) or `local is not GLOBAL`."""
    b: dict[str, Any] = builtins_of(g)

    def is_local_global(fr: Frame) -> Any:
        try:
            v: Any = fr[lname]
        except KeyError:
            raise unbound_local(lname) from None
        if gname in g:
            w: Any = g[gname]
        elif gname in b:
            w = b[gname]
        else:
            w = global_fallback(gname, g, b)
        if is_op:
            return v is w
        return v is not w
    return is_local_global


# `expression OP constant`

def make_is_const(lc: ExprFn, c: Any) -> ExprFn:
    """`left is c`."""
    def is_c(fr: Frame) -> Any:
        return lc(fr) is c
    return is_c


def make_is_not_const(lc: ExprFn, c: Any) -> ExprFn:
    """`left is not c`."""
    def is_not_c(fr: Frame) -> Any:
        return lc(fr) is not c
    return is_not_c


def make_eq_const(lc: ExprFn, c: Any) -> ExprFn:
    """`left == c`."""
    def eq_c(fr: Frame) -> Any:
        return lc(fr) == c
    return eq_c


CONST_COMPARES: dict[str, ConstFactory] = {
    'is': make_is_const, 'is not': make_is_not_const, '==': make_eq_const,
}
"""Closure factories for `expression OP constant`, by operator."""


# `expression OP expression`

def make_lt(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left < right`."""
    def lt(fr: Frame) -> Any:
        return lc(fr) < rc(fr)
    return lt


def make_gt(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left > right`."""
    def gt(fr: Frame) -> Any:
        return lc(fr) > rc(fr)
    return gt


def make_eq(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left == right`."""
    def eq(fr: Frame) -> Any:
        return lc(fr) == rc(fr)
    return eq


def make_ne(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left != right`."""
    def ne(fr: Frame) -> Any:
        return lc(fr) != rc(fr)
    return ne


def make_le(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left <= right`."""
    def le(fr: Frame) -> Any:
        return lc(fr) <= rc(fr)
    return le


def make_ge(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left >= right`."""
    def ge(fr: Frame) -> Any:
        return lc(fr) >= rc(fr)
    return ge


def make_is(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left is right`."""
    def is_(fr: Frame) -> Any:
        return lc(fr) is rc(fr)
    return is_


def make_is_not(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left is not right`."""
    def is_not(fr: Frame) -> Any:
        return lc(fr) is not rc(fr)
    return is_not


def make_in(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left in right`."""
    def in_(fr: Frame) -> Any:
        return lc(fr) in rc(fr)
    return in_


def make_not_in(lc: ExprFn, rc: ExprFn) -> ExprFn:
    """`left not in right`."""
    def not_in(fr: Frame) -> Any:
        return lc(fr) not in rc(fr)
    return not_in


PAIR_COMPARES: dict[str, PairFactory] = {
    '<': make_lt, '>': make_gt, '==': make_eq, '!=': make_ne, '<=': make_le, '>=': make_ge,
    'is': make_is, 'is not': make_is_not, 'in': make_in, 'not in': make_not_in,
}
"""Closure factories for `expression OP expression`, by operator."""


def make_chain(lc: ExprFn, pairs: list[tuple[BinaryFn, ExprFn]]) -> ExprFn:
    """A chained comparison `left OP1 c1 OP2 c2 ...`: pairs holds each
    operator's host function with the closure of its right operand."""
    def chain(fr: Frame) -> Any:
        a: Any = lc(fr)
        r: Any = True
        for fn, c in pairs:
            b: Any = c(fr)
            r = fn(a, b)
            if not r:
                return r
            a = b
        return r
    return chain
