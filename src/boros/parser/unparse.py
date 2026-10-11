"""Turning an expression back into source text, for postponed annotations.

Under `from __future__ import annotations` an annotation is not evaluated:
it is stored as a string holding its source, normalized the way CPython
writes it (`dict[str, int] | None`, `'str'`, `tuple[int, ...]`).  `unparse`
rebuilds that text from the syntax tree.  Operands are parenthesized only
where precedence requires it, using the levels below (loosest first).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..syntax import (
    Attribute,
    BinOp,
    BoolOp,
    Call,
    Compare,
    Const,
    DictDisplay,
    IfExp,
    List,
    Name,
    SetDisplay,
    Slice,
    Starred,
    Subscript,
    Tuple,
    UnaryOp,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..syntax import Expression

PREC_TUPLE: int = 1
PREC_TEST: int = 2
PREC_OR: int = 3
PREC_AND: int = 4
PREC_NOT: int = 5
PREC_CMP: int = 6
PREC_FACTOR: int = 13
PREC_POWER: int = 14
PREC_ATOM: int = 16

# binding strength of each binary operator (between PREC_CMP and PREC_FACTOR)
BINARY_PREC: dict[str, int] = {'|': 7, '^': 8, '&': 9, '<<': 10, '>>': 10, '+': 11, '-': 11, '*': 12, '/': 12,
                               '//': 12, '%': 12, '@': 12, '**': PREC_POWER}


def unparse(n: Expression) -> str:
    """The source text of expression n, as CPython stores a postponed annotation."""
    return unparse_at(n, PREC_TEST)


def unparse_at(n: Expression, level: int) -> str:
    """The source text of n where an expression binding at least as tightly
    as `level` is needed (anything looser is parenthesized)."""
    f: Callable[[Any, int], str] | None = UNPARSERS.get(type(n))
    if f is None:
        return '...'
    return f(n, level)


def parenthesize(text: str, prec: int, level: int) -> str:
    """text, an expression of precedence prec, in parentheses if the context needs a tighter one."""
    if prec < level:
        return f'({text})'
    return text


def joined(items: list[Expression]) -> str:
    """Comma-separated items, as in a call, list or tuple."""
    return ', '.join([unparse_at(x, PREC_TEST) for x in items])


def unparse_name(n: Name, level: int) -> str:
    return n.id


def unparse_const(n: Const, level: int) -> str:
    if n.value is Ellipsis:
        return '...'
    return repr(n.value)


def unparse_attribute(n: Attribute, level: int) -> str:
    return f'{unparse_at(n.value, PREC_ATOM)}.{n.attr}'


def unparse_subscript(n: Subscript, level: int) -> str:
    index: Expression = n.index
    if type(index) is Tuple and index.elts:
        inner: str = joined(index.elts)
    else:
        inner = unparse_at(index, PREC_TUPLE)
    return f'{unparse_at(n.value, PREC_ATOM)}[{inner}]'


def unparse_slice(n: Slice, level: int) -> str:
    parts: list[str] = ['' if x is None else unparse_at(x, PREC_TEST) for x in (n.lower, n.upper)]
    if n.step is not None:
        parts.append(unparse_at(n.step, PREC_TEST))
    return ':'.join(parts)


def unparse_call(n: Call, level: int) -> str:
    parts: list[str] = [unparse_at(a, PREC_TEST) for a in n.args]
    for k in n.keywords:
        prefix: str = '**' if k.arg is None else k.arg + '='
        parts.append(prefix + unparse_at(k.value, PREC_TEST))
    return f"{unparse_at(n.func, PREC_ATOM)}({', '.join(parts)})"


def unparse_starred(n: Starred, level: int) -> str:
    return '*' + unparse_at(n.value, PREC_CMP + 1)


def unparse_tuple(n: Tuple, level: int) -> str:
    if len(n.elts) == 1:
        return f'({unparse_at(n.elts[0], PREC_TEST)},)'
    return f'({joined(n.elts)})'


def unparse_list(n: List, level: int) -> str:
    return f'[{joined(n.elts)}]'


def unparse_set(n: SetDisplay, level: int) -> str:
    return '{' + joined(n.elts) + '}'


def unparse_dict(n: DictDisplay, level: int) -> str:
    items: list[str] = []
    for k, v in zip(n.keys, n.values):
        if k is None:
            items.append('**' + unparse_at(v, PREC_CMP + 1))
        else:
            items.append(f'{unparse_at(k, PREC_TEST)}: {unparse_at(v, PREC_TEST)}')
    return '{' + ', '.join(items) + '}'


def unparse_binop(n: BinOp, level: int) -> str:
    prec: int = BINARY_PREC[n.op]
    # operators group to the left, except ** which groups to the right
    left_prec: int = prec + 1 if n.op == '**' else prec
    right_prec: int = prec if n.op == '**' else prec + 1
    text: str = f'{unparse_at(n.left, left_prec)} {n.op} {unparse_at(n.right, right_prec)}'
    return parenthesize(text, prec, level)


def unparse_unaryop(n: UnaryOp, level: int) -> str:
    if n.op == 'not':
        return parenthesize('not ' + unparse_at(n.operand, PREC_NOT), PREC_NOT, level)
    return parenthesize(n.op + unparse_at(n.operand, PREC_FACTOR), PREC_FACTOR, level)


def unparse_boolop(n: BoolOp, level: int) -> str:
    prec: int = PREC_OR if n.op == 'or' else PREC_AND
    text: str = f' {n.op} '.join([unparse_at(v, prec + 1) for v in n.values])
    return parenthesize(text, prec, level)


def unparse_compare(n: Compare, level: int) -> str:
    parts: list[str] = [unparse_at(n.left, PREC_CMP + 1)]
    for op, c in zip(n.ops, n.comparators):
        parts.append(f'{op} {unparse_at(c, PREC_CMP + 1)}')
    return parenthesize(' '.join(parts), PREC_CMP, level)


def unparse_ifexp(n: IfExp, level: int) -> str:
    text: str = (f'{unparse_at(n.body, PREC_TEST + 1)} if {unparse_at(n.test, PREC_TEST + 1)} '
                 f'else {unparse_at(n.orelse, PREC_TEST)}')
    return parenthesize(text, PREC_TEST, level)


UNPARSERS: dict[type, Callable[[Any, int], str]] = {
    Name: unparse_name, Const: unparse_const, Attribute: unparse_attribute, Subscript: unparse_subscript,
    Slice: unparse_slice, Call: unparse_call, Starred: unparse_starred, Tuple: unparse_tuple, List: unparse_list,
    SetDisplay: unparse_set, DictDisplay: unparse_dict, BinOp: unparse_binop, UnaryOp: unparse_unaryop,
    BoolOp: unparse_boolop, Compare: unparse_compare, IfExp: unparse_ifexp,
}
"""The unparse function of each kind of expression; other kinds become '...'."""
