"""Parsing of expressions.

Python's expression grammar is a ladder of precedence levels.  Each level is
one method that parses the next, tighter-binding level and then looks for its
own operators, so the methods below read from the loosest to the tightest:

    test             `a if b else c`, `lambda: ...`
    or_test          `a or b`
    and_test         `a and b`
    not_test         `not a`
    comparison       `a < b == c`, `a in b`, `a is not b`
    expr / binary    `| ^ & << >> + - * / // % @`, by precedence climbing
    factor           `-a`, `+a`, `~a`
    power            `await a`, `a ** b`
    primary          trailers: `a.name`, `a(args)`, `a[index]`
    atom             names, numbers, strings, `(...)`, `[...]`, `{...}`

All binary operators share the single method `binary`, which climbs the
BINARY_PRECEDENCE table instead of needing one method per level.

Besides building syntax nodes, the parser records name-binding facts in the
current Scope (walrus targets, `yield` and `await`, uses of `super` and
`__class__`), which the compiler later uses to resolve names.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core_types import Token
from ..lexer import parse_number
from ..syntax import (
    Arguments,
    Attribute,
    Await,
    BinOp,
    BoolOp,
    Call,
    Compare,
    Comprehension,
    Const,
    DictComp,
    DictDisplay,
    Expression,
    GeneratorExp,
    IfExp,
    Keyword,
    Lambda,
    List,
    ListComp,
    Name,
    NamedExpr,
    Node,
    Scope,
    SetComp,
    SetDisplay,
    Slice,
    Starred,
    Subscript,
    Tuple,
    UnaryOp,
    Yield,
    YieldFrom,
    collect_target_names,
)
from .base import BINARY_PRECEDENCE, COMPARE_OPS, EXPR_END, KEYWORDS, ParserBase

if TYPE_CHECKING:
    from typing import NoReturn

# The keywords that are literal constants.
KEYWORD_CONSTANTS: dict[str, Any] = {'None': None, 'True': True, 'False': False}


class ExpressionParser(ParserBase):
    """Parsing of expressions (a mixin of boros.parser.Parser)."""

    # -- expression lists and assignment targets -----------------------------

    def testlist_star_expr(self) -> Expression:
        """Parse `a, *b, c`: a single expression, or a Tuple if there is a comma.

        A trailing comma is allowed, so `x = 1,` assigns a one-element tuple."""
        line: int = self.tok[2]
        e: Expression = self.test_or_star()
        if self.tok[1] != ',':
            return e
        elts: list[Expression] = [e]
        while self.accept(','):
            if self.tok[0] == 'NEWLINE' or self.tok[1] in EXPR_END:
                break
            elts.append(self.test_or_star())
        return Tuple(line, elts)

    def testlist(self) -> Expression:
        """Parse a comma-separated expression list (the same grammar as testlist_star_expr)."""
        return self.testlist_star_expr()

    def test_or_star(self) -> Expression:
        """Parse one item of an expression list: `*iterable` or a (named) expression."""
        if self.tok[1] == '*':
            line: int = self.advance()[2]
            return Starred(line, self.expr())
        return self.namedexpr_test()

    def target_list(self) -> Expression:
        """Parse the target of a `for` loop or comprehension: `a`, `a, b` or `a, *b`."""
        line: int = self.tok[2]
        e: Expression = self.target()
        if self.tok[1] != ',':
            return e
        elts: list[Expression] = [e]
        while self.accept(','):
            if self.tok[1] == 'in' or self.tok[1] == '=' or self.tok[1] in EXPR_END:
                break
            elts.append(self.target())
        return Tuple(line, elts)

    def target(self) -> Expression:
        """Parse one assignment target: an expression, optionally starred."""
        if self.tok[1] == '*':
            line: int = self.advance()[2]
            return Starred(line, self.expr())
        return self.expr()

    def exprlist(self, as_list: bool) -> list[Expression]:
        """Parse the comma-separated targets of a `del` statement.

        The result is always a list; `as_list` is accepted for compatibility."""
        elts: list[Expression] = [self.target()]
        while self.accept(','):
            if self.tok[0] == 'NEWLINE' or self.tok[1] in EXPR_END:
                break
            elts.append(self.target())
        return elts

    # -- conditional expressions, lambdas and assignment expressions ----------

    def namedexpr_test(self) -> Expression:
        """Parse an expression that may be an assignment expression `name := value`.

        The walrus target is recorded as assigned in the current scope.  The
        parser gives comprehensions no scope of their own, so (as in Python)
        a walrus inside a comprehension binds in the enclosing function."""
        e: Expression = self.test()
        if self.tok[1] != ':=':
            return e
        line: int = self.advance()[2]
        target: Name = self.walrus_target(e)
        value: Expression = self.test()
        self.scope.assigned.add(target.id)
        return NamedExpr(line, target, value)

    def or_test_walrus(self) -> Expression:
        """Parse a comprehension condition: an or_test, optionally `name := value`."""
        e: Expression = self.or_test()
        if self.tok[1] != ':=':
            return e
        line: int = self.advance()[2]
        target: Name = self.walrus_target(e)
        value: Expression = self.or_test()
        self.scope.assigned.add(target.id)
        return NamedExpr(line, target, value)

    def walrus_target(self, e: Expression) -> Name:
        """Check that the left-hand side of `:=` is a plain name, which is
        stored to, not loaded."""
        if type(e) is not Name:
            self.error(f'cannot use assignment expressions with {type(e).__name__.lower()}')
        self.unuse(e.id)
        return e

    def test(self) -> Expression:
        """Parse a conditional expression `body if cond else orelse`, or a lambda."""
        if self.tok[1] == 'lambda':
            return self.lambdef()
        line: int = self.tok[2]
        x: Expression = self.or_test()
        if self.tok[1] != 'if':
            return x
        self.advance()
        cond: Expression = self.or_test()
        self.expect('else')
        orelse: Expression = self.test()
        return IfExp(line, cond, x, orelse)

    def lambdef(self) -> Lambda:
        """Parse `lambda params: body`, parsing the body in a new function scope."""
        line: int = self.advance()[2]
        scope: Scope = Scope('function', '<lambda>', self.scope)
        args: Arguments = self.parameters(':', False, scope)
        self.expect(':')
        saved: Scope = self.scope
        self.scope = scope
        body: Expression = self.test()
        self.scope = saved
        return Lambda(line, args, body, scope)

    # -- boolean operators and comparisons -------------------------------------

    def or_test(self) -> Expression:
        """Parse `a or b or ...` into a single BoolOp over all the operands."""
        x: Expression = self.and_test()
        if self.tok[1] != 'or':
            return x
        line: int = self.tok[2]
        values: list[Expression] = [x]
        while self.accept('or'):
            values.append(self.and_test())
        return BoolOp(line, 'or', values)

    def and_test(self) -> Expression:
        """Parse `a and b and ...` into a single BoolOp over all the operands."""
        x: Expression = self.not_test()
        if self.tok[1] != 'and':
            return x
        line: int = self.tok[2]
        values: list[Expression] = [x]
        while self.accept('and'):
            values.append(self.not_test())
        return BoolOp(line, 'and', values)

    def not_test(self) -> Expression:
        """Parse `not x` (which binds looser than comparisons) or a comparison."""
        if self.tok[1] == 'not':
            line: int = self.advance()[2]
            return UnaryOp(line, 'not', self.not_test())
        return self.comparison()

    def comparison(self) -> Expression:
        """Parse a comparison chain such as `a < b <= c` into one Compare node.

        Python evaluates a chain as `a < b and b <= c` with `b` evaluated once,
        so the node keeps the operands and operators side by side."""
        x: Expression = self.expr()
        t: Token = self.tok
        if t[1] not in COMPARE_OPS or t[0] == 'STRING' or t[0] == 'NUMBER':
            return x
        line: int = t[2]
        ops: list[str] = []
        comps: list[Expression] = []
        while t[1] in COMPARE_OPS and t[0] != 'STRING' and t[0] != 'NUMBER':
            ops.append(self.compare_op())
            comps.append(self.expr())
            t = self.tok
        return Compare(line, x, ops, comps)

    def compare_op(self) -> str:
        """Consume one comparison operator, joining the two-word `not in` and `is not`."""
        v: str = self.advance()[1]
        if v == 'not':
            self.expect('in')
            return 'not in'
        if v == 'is' and self.accept('not'):
            return 'is not'
        return v

    # -- arithmetic and bitwise operators ---------------------------------------

    def expr(self) -> Expression:
        """Parse an expression built from binary operators, such as `a + b * c`."""
        return self.binary(1)

    def binary(self, minprec: int) -> Expression:
        """Parse operands joined by binary operators of precedence `minprec` or higher.

        This is precedence climbing: after an operand, any operator whose
        precedence p is at least `minprec` is consumed and its right operand
        is parsed with minimum precedence p + 1.  Tighter operators therefore
        group first and operators of equal precedence group to the left:
        `a + b * c` is `a + (b * c)` and `a - b - c` is `(a - b) - c`."""
        left: Expression = self.factor()
        while True:
            t: Token = self.tok
            if t[0] != 'OP':
                return left
            prec: int | None = BINARY_PRECEDENCE.get(t[1])
            if prec is None or prec < minprec:
                return left
            self.advance()
            right: Expression = self.binary(prec + 1)
            left = BinOp(t[2], left, t[1], right)

    def factor(self) -> Expression:
        """Parse the unary operators `-x`, `+x` and `~x`.

        A minus sign applied to a numeric literal is folded into a negative
        constant, so `-1` is the constant -1 rather than an operation."""
        t: Token = self.tok
        v: Any = t[1]
        if t[0] == 'OP' and (v == '-' or v == '+' or v == '~'):
            self.advance()
            operand: Expression = self.factor()
            if v == '-' and type(operand) is Const:
                cv: Any = operand.value
                ct: type = type(cv)
                if ct is int or ct is float or ct is complex:
                    return Const(t[2], -cv)
            return UnaryOp(t[2], v, operand)
        return self.power()

    def power(self) -> Expression:
        """Parse `await x` and the power operator `x ** y`.

        The right operand of `**` is a `factor`, so `**` is right-associative
        (`a ** b ** c` is `a ** (b ** c)`) and binds tighter than a unary minus
        on its left but looser than one on its right: `-x ** -y` is
        `-(x ** (-y))`."""
        t: Token = self.tok
        if t[1] == 'await' and t[0] == 'NAME':
            x: Expression = self.await_expr()
        else:
            x = self.primary()
        if self.tok[1] == '**':
            line: int = self.advance()[2]
            return BinOp(line, x, '**', self.factor())
        return x

    def await_expr(self) -> Await:
        """Parse `await x`, which is only allowed in an async function (whose
        body runs in generator mode)."""
        if not self.scope.is_async:
            self.error("'await' outside async function" if self.scope.kind == 'function' else "'await' outside function")
        line: int = self.advance()[2]
        self.scope.is_gen = True
        return Await(line, self.primary())

    # -- trailers: attribute access, calls and subscripts ----------------------

    def primary(self) -> Expression:
        """Parse an atom followed by any number of trailers: `.name`, `(args)`, `[index]`.

        Names of the form `__private` are mangled with the enclosing class name."""
        x: Expression = self.atom()
        while True:
            t: Token = self.tok
            v: Any = t[1]
            if t[0] != 'OP':
                return x
            if v == '.':
                self.advance()
                name: str = self.expect_name()
                if name[0] == '_' and name[:2] == '__':
                    name = self.mangle(name)
                x = Attribute(t[2], x, name)
            elif v == '(':
                self.advance()
                args, keywords = self.call_args()
                x = Call(t[2], x, args, keywords)
            elif v == '[':
                self.advance()
                x = Subscript(t[2], x, self.subscript_list())
            else:
                return x

    def call_args(self) -> tuple[list[Expression], list[Keyword]]:
        """Parse call arguments up to and including `)`; the `(` has been consumed.

        Arguments are positional values, `*iterable`, `name=value` or
        `**mapping`.  A generator expression may appear without its own
        parentheses, as in `sum(x for x in xs)`."""
        args: list[Expression] = []
        keywords: list[Keyword] = []
        while self.tok[1] != ')':
            t: Token = self.tok
            if t[1] == '*' and t[0] == 'OP':
                if keywords and any(k.arg is None for k in keywords):
                    self.error('iterable argument unpacking follows keyword argument unpacking')
                self.advance()
                args.append(Starred(t[2], self.test()))
            elif t[1] == '**' and t[0] == 'OP':
                self.advance()
                keywords.append(Keyword(t[2], None, self.test()))
            elif t[0] == 'NAME' and self.peek()[1] == '=' and self.peek()[0] == 'OP':
                if keywords and any(k.arg == t[1] for k in keywords):
                    self.error(f'keyword argument repeated: {t[1]}')
                self.advance()
                self.advance()
                keywords.append(Keyword(t[2], t[1], self.test()))
            else:
                if keywords:
                    self.positional_after_keyword(keywords)
                a: Expression = self.namedexpr_test()
                if self.tok[1] == 'for' or (self.tok[1] == 'async' and self.peek()[1] == 'for'):
                    a = self.call_genexp(t, a, args)
                args.append(a)
            if not self.accept(','):
                break
        self.expect(')')
        return args, keywords

    def positional_after_keyword(self, keywords: list[Keyword]) -> NoReturn:
        """Reject a positional call argument after the keyword arguments `keywords`."""
        if any(k.arg is None for k in keywords):
            self.error('positional argument follows keyword argument unpacking')
        self.error('positional argument follows keyword argument')

    def call_genexp(self, t: Token, elt: Expression, args: list[Expression]) -> GeneratorExp:
        """Parse a generator expression with element `elt` (which started at
        token t) passed to a call without parentheses of its own, which is
        allowed only when it is the only argument (`args` are the ones before it)."""
        gens: list[Comprehension] = self.comp_for()
        self.check_comprehension([elt], gens)
        if args or self.tok[1] == ',':
            self.error('Generator expression must be parenthesized')
        return GeneratorExp(t[2], elt, gens)

    def subscript_list(self) -> Expression:
        """Parse a subscription index up to and including `]`.

        Several comma-separated items form a Tuple index: `a[1:2, 3]`."""
        line: int = self.tok[2]
        items: list[Expression] = [self.subscript()]
        is_tuple: bool = False
        while self.accept(','):
            is_tuple = True
            if self.tok[1] == ']':
                break
            items.append(self.subscript())
        self.expect(']')
        if is_tuple:
            return Tuple(line, items)
        return items[0]

    def subscript(self) -> Expression:
        """Parse one subscript item: an expression, `*iterable`, or a slice."""
        line: int = self.tok[2]
        if self.tok[1] == '*':
            self.advance()
            return Starred(line, self.expr())
        if self.tok[1] == ':':
            return self.slice_rest(line, None)
        lower: Expression = self.namedexpr_test()
        if self.tok[1] == ':':
            return self.slice_rest(line, lower)
        return lower

    def slice_rest(self, line: int, lower: Expression | None) -> Slice:
        """Parse the `:upper:step` part of a slice, each part optional; the current token is the first `:`."""
        self.advance()
        upper: Expression | None = None
        step: Expression | None = None
        v: Any = self.tok[1]
        if v != ':' and v != ']' and v != ',':
            upper = self.test()
        if self.accept(':'):
            v = self.tok[1]
            if v != ']' and v != ',':
                step = self.test()
        return Slice(line, lower, upper, step)

    # -- comprehensions and yield --------------------------------------------------

    def comp_for(self) -> list[Comprehension]:
        """Parse the `for target in iterable if condition...` clauses of a comprehension.

        `async for` clauses are marked is_async."""
        gens: list[Comprehension] = []
        while True:
            is_async: bool = False
            if self.tok[1] == 'async':
                self.advance()
                is_async = True
            if self.tok[1] != 'for':
                break
            line: int = self.advance()[2]
            target: Expression = self.target_list()
            self.check_target(target)
            self.expect('in')
            it: Expression = self.or_test()
            ifs: list[Expression] = []
            while self.tok[1] == 'if':
                self.advance()
                ifs.append(self.or_test_walrus())
            gens.append(Comprehension(line, target, it, ifs, is_async))
        return gens

    def check_comprehension(self, elts: list[Expression], gens: list[Comprehension]) -> None:
        """CPython's compile-time checks of a comprehension with element (or
        key and value) `elts` and clauses `gens`: no starred element, and
        PEP 572's restrictions on assignment expressions.  The loads of
        names that belong to the comprehension's own scope are then no
        longer counted for the current scope (see `atom`)."""
        for e in elts:
            if type(e) is Starred:
                self.error('iterable unpacking cannot be used in comprehension')
        for g in gens:
            if find_named_exprs(g.iter, []):
                self.error('assignment expression cannot be used in a comprehension iterable expression')
        walruses: list[NamedExpr] = comprehension_named_exprs(elts, gens)
        if walruses:
            self.check_comprehension_walruses(walruses, gens)
        self.forget_comprehension_loads(elts, gens)

    def forget_comprehension_loads(self, elts: list[Expression], gens: list[Comprehension]) -> None:
        """Stop counting, for the current scope, the loads of names parsed
        in a comprehension's own scope: all of it but its first iterable.
        (Its targets were not counted, see comp_for.)"""
        names: list[str] = []
        for e in elts:
            scope_loads(e, names)
        for i, g in enumerate(gens):
            for c in g.ifs:
                scope_loads(c, names)
            if i > 0:
                scope_loads(g.iter, names)
        for x in names:
            self.unuse(x)

    def check_comprehension_walruses(self, walruses: list[NamedExpr], gens: list[Comprehension]) -> None:
        """An assignment expression in a comprehension binds in the enclosing
        function, so it is not allowed in a class body and must not rebind
        an iteration variable of the comprehension."""
        if self.scope.kind == 'class':
            self.error('assignment expression within a comprehension cannot be used in a class body')
        bound: set[str] = set()
        for g in gens:
            collect_target_names(g.target, bound)
        for w in walruses:
            if w.target.id in bound:
                self.error(f"assignment expression cannot rebind comprehension iteration variable '{w.target.id}'")

    def at_comprehension(self) -> bool:
        """Does a comprehension clause (`for` or `async for`) start at the current token?"""
        return self.tok[1] == 'for' or self.tok[1] == 'async'

    def yield_expr(self) -> Expression:
        """Parse `yield`, `yield value` or `yield from iterable`.

        A yield makes the enclosing function a generator: the scope is
        marked so that the compiler builds its body in generator mode."""
        line: int = self.advance()[2]
        self.scope.is_gen = True
        self.scope.has_yield = True
        if self.accept('from'):
            return YieldFrom(line, self.test())
        if self.tok[0] == 'NEWLINE' or self.tok[1] in EXPR_END:
            return Yield(line, None)
        return Yield(line, self.testlist_star_expr())

    # -- atoms -------------------------------------------------------------------

    def atom(self) -> Expression:
        """Parse an atom: a name, a constant, a string, or a bracketed display.

        Names, the most common atoms, are handled here directly.  A use of
        `super` or `__class__` marks the scope as needing the enclosing class
        (the implicit `__class__` cell), and private names are mangled.  The
        name is recorded as loaded in the scope (see `check_declaration`)."""
        t: Token = self.tok
        kind: str = t[0]
        if kind == 'NAME':
            v: str = t[1]
            if v in KEYWORDS:
                return self.keyword_constant(v, t[2])
            self.advance()
            if v[0] == '_' and v[:2] == '__':
                if v == '__class__':
                    self.scope.uses_class = True
                v = self.mangle(v)
            elif v == 'super':
                self.scope.uses_class = True
            self.scope.loads.append(v)
            return Name(t[2], v)
        if kind == 'NUMBER':
            return self.number_atom(t)
        if kind == 'STRING':
            return self.strings()
        if kind == 'OP':
            return self.bracket_atom(t)
        self.error()

    def bracket_atom(self, t: Token) -> Expression:
        """Parse an atom that starts with an operator token: `(...)`, `[...]`, `{...}` or `...`."""
        v: Any = t[1]
        if v == '(':
            return self.paren_atom()
        if v == '[':
            return self.list_display()
        if v == '{':
            return self.brace_display()
        if v == '...':
            self.advance()
            return Const(t[2], Ellipsis)
        self.error()

    def keyword_constant(self, v: str, line: int) -> Const:
        """Parse the keyword `v` where an atom is expected: only None, True and False are valid."""
        if v in KEYWORD_CONSTANTS:
            self.advance()
            return Const(line, KEYWORD_CONSTANTS[v])
        if v == 'yield':
            self.error("'yield' outside parentheses")
        self.error()

    def number_atom(self, t: Token) -> Const:
        """Parse a numeric literal into a constant."""
        self.advance()
        try:
            return Const(t[2], parse_number(t[1]))
        except ValueError:
            self.error(f'invalid number literal {t[1]!r}', t)

    def display_items(self, first: Expression, closer: str) -> list[Expression]:
        """Parse the rest of a bracketed display after its first item, up to and including `closer`.

        Items may be starred, and a trailing comma is allowed."""
        elts: list[Expression] = [first]
        while self.accept(','):
            if self.tok[1] == closer:
                break
            elts.append(self.test_or_star())
        self.expect(closer)
        return elts

    def paren_atom(self) -> Expression:
        """Parse a parenthesized form: `()`, `(x)`, `(x, y)`, `(yield x)` or `(x for x in y)`."""
        line: int = self.advance()[2]
        if self.accept(')'):
            return Tuple(line, [])
        if self.tok[1] == 'yield':
            y: Expression = self.yield_expr()
            self.expect(')')
            return y
        e: Expression = self.test_or_star()
        if self.at_comprehension():
            gen: GeneratorExp = GeneratorExp(line, e, self.comp_for())
            self.check_comprehension([e], gen.gens)
            self.expect(')')
            return gen
        if self.tok[1] == ',':
            return Tuple(line, self.display_items(e, ')'))
        self.expect(')')
        if type(e) is Starred:
            self.error('cannot use starred expression here')
        return e

    def list_display(self) -> Expression:
        """Parse a list display `[a, *b]` or a list comprehension `[x for x in y]`."""
        line: int = self.advance()[2]
        if self.accept(']'):
            return List(line, [])
        e: Expression = self.test_or_star()
        if self.at_comprehension():
            gens: list[Comprehension] = self.comp_for()
            self.check_comprehension([e], gens)
            self.expect(']')
            return ListComp(line, e, gens)
        return List(line, self.display_items(e, ']'))

    def brace_display(self) -> Expression:
        """Parse a display in braces: a dict, a set, or a dict or set comprehension.

        The first item decides which: `{}` and `{k: v ...}` and `{**m ...}`
        are dicts, anything else (including `{*a}`) is a set."""
        line: int = self.advance()[2]
        if self.accept('}'):
            return DictDisplay(line, [], [])
        if self.accept('**'):
            return self.dict_display(line, None, self.expr())
        key: Expression = self.test_or_star()
        if self.tok[1] != ':' or type(key) is Starred:
            return self.set_display(line, key)
        self.advance()
        value: Expression = self.test()
        if self.at_comprehension():
            gens: list[Comprehension] = self.comp_for()
            self.check_comprehension([key, value], gens)
            self.expect('}')
            return DictComp(line, key, value, gens)
        return self.dict_display(line, key, value)

    def set_display(self, line: int, first: Expression) -> Expression:
        """Parse the rest of a set display or set comprehension after its first item."""
        if self.at_comprehension():
            gens: list[Comprehension] = self.comp_for()
            self.check_comprehension([first], gens)
            self.expect('}')
            return SetComp(line, first, gens)
        return SetDisplay(line, self.display_items(first, '}'))

    def dict_display(self, line: int, key: Expression | None, value: Expression) -> DictDisplay:
        """Parse the rest of a dict display after its first entry.

        Entries are `key: value` or `**mapping`; the latter is stored with a key of None."""
        keys: list[Expression | None] = [key]
        values: list[Expression] = [value]
        while self.accept(','):
            if self.tok[1] == '}':
                break
            if self.accept('**'):
                keys.append(None)
                values.append(self.expr())
            else:
                keys.append(self.test())
                self.expect(':')
                values.append(self.test())
        self.expect('}')
        return DictDisplay(line, keys, values)


# -- walking parsed expressions, for the checks of comprehensions --------------------

def child_nodes(n: Node) -> list[Node]:
    """The syntax nodes directly inside node n."""
    out: list[Node] = []
    for f in type(n)._fields:
        v: Any = getattr(n, f)
        if isinstance(v, Node):
            out.append(v)
        elif type(v) is list:
            out.extend([x for x in v if isinstance(x, Node)])
    return out


def find_named_exprs(n: Node, out: list[NamedExpr]) -> list[NamedExpr]:
    """Append the assignment expressions in n (not looking inside lambdas)
    to `out`, and return it."""
    if type(n) is not Lambda:
        if type(n) is NamedExpr:
            out.append(n)
        for c in child_nodes(n):
            find_named_exprs(c, out)
    return out


def comprehension_named_exprs(elts: list[Expression], gens: list[Comprehension]) -> list[NamedExpr]:
    """The assignment expressions in the elements and conditions of a comprehension."""
    out: list[NamedExpr] = []
    for e in elts:
        find_named_exprs(e, out)
    for g in gens:
        for c in g.ifs:
            find_named_exprs(c, out)
    return out


def scope_loads(n: Node, out: list[str]) -> None:
    """Append to `out` the names that the parser counted as loads in the
    current scope while parsing n: not those in the body of a lambda (which
    has a scope of its own) or the target of an assignment expression, and
    of a nested comprehension only those in its first iterable (the others
    were forgotten when it was parsed)."""
    children: list[Node]
    if type(n) is Name:
        out.append(n.id)
        return
    if type(n) is Lambda:
        children = [d for d in n.args.defaults + n.args.kw_defaults if d is not None]
    elif type(n) is ListComp or type(n) is SetComp or type(n) is DictComp or type(n) is GeneratorExp:
        children = [n.gens[0].iter]
    elif type(n) is NamedExpr:
        children = [n.value]
    else:
        children = child_nodes(n)
    for c in children:
        scope_loads(c, out)
