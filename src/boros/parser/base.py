"""Token-stream helpers shared by all parts of the recursive-descent parser.

The parser reads the token list produced by `boros.lexer.tokenize` from
left to right, one grammar rule per method, looking at the current token
(`tok`) and occasionally one or two ahead (`peek`).  While parsing it also
records name-binding facts in the current `Scope` (which names a function
assigns, declares global, and so on), so the compiler can later decide
where each variable lives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core_types import Token
from ..lexer import syntax_error
from ..syntax import (
    Arguments,
    Attribute,
    Await,
    Call,
    Compare,
    Const,
    DictComp,
    DictDisplay,
    Expression,
    GeneratorExp,
    IfExp,
    JoinedStr,
    Keyword,
    Lambda,
    List,
    ListComp,
    Match,
    Name,
    NamedExpr,
    Scope,
    SetComp,
    SetDisplay,
    Starred,
    Statement,
    Subscript,
    Tuple,
    Yield,
    YieldFrom,
)

if TYPE_CHECKING:
    from typing import Any, NoReturn

# binding strength of the binary operators, loosest first ('**' is handled separately)
BINARY_PRECEDENCE: dict[str, int] = {
    '|': 1, '^': 2, '&': 3, '<<': 4, '>>': 4, '+': 5, '-': 5,
    '*': 6, '/': 6, '//': 6, '%': 6, '@': 6,
}


# the tokens that can start a comparison operator ('not in' and 'is not' start with 'not' / 'is')
COMPARE_OPS: dict[str, int] = {'<': 1, '>': 1, '==': 1, '>=': 1, '<=': 1, '!=': 1, 'in': 1, 'not': 1, 'is': 1}


# augmented assignment operators and the binary operator each one applies
AUG_OPS: dict[str, str] = {'+=': '+', '-=': '-', '*=': '*', '/=': '/', '//=': '//', '%=': '%', '**=': '**',
                          '>>=': '>>', '<<=': '<<', '&=': '&', '^=': '^', '|=': '|', '@=': '@'}


# the hard keywords, which cannot be used as names
KEYWORDS: dict[str, int] = {
    'False': 1, 'None': 1, 'True': 1, 'and': 1, 'as': 1, 'assert': 1, 'async': 1,
    'await': 1, 'break': 1, 'class': 1, 'continue': 1, 'def': 1, 'del': 1, 'elif': 1,
    'else': 1, 'except': 1, 'finally': 1, 'for': 1, 'from': 1, 'global': 1, 'if': 1,
    'import': 1, 'in': 1, 'is': 1, 'lambda': 1, 'nonlocal': 1, 'not': 1, 'or': 1,
    'pass': 1, 'raise': 1, 'return': 1, 'try': 1, 'while': 1, 'with': 1, 'yield': 1,
}


# tokens that can end an expression list (used to detect a bare `yield`/`return`)
EXPR_END: dict[str, int] = {')': 1, ']': 1, '}': 1, '=': 1, ';': 1, ':': 1, ',': 1}


# How CPython's error messages describe the expressions that cannot be
# assigned to or deleted (anything not listed here is an 'expression').
TARGET_DESCRIPTIONS: dict[type, str] = {
    Call: 'function call', Compare: 'comparison', IfExp: 'conditional expression', Lambda: 'lambda',
    Yield: 'yield expression', YieldFrom: 'yield expression', Await: 'await expression',
    NamedExpr: 'named expression', ListComp: 'list comprehension', SetComp: 'set comprehension',
    DictComp: 'dict comprehension', GeneratorExp: 'generator expression', DictDisplay: 'dict literal',
    SetDisplay: 'set display', JoinedStr: 'f-string expression', Const: 'literal',
}


def target_description(t: Expression) -> str:
    """How an error message describes the invalid target t, such as
    'function call' or 'True'."""
    if type(t) is Const:
        v: Any = t.value
        if v is None or v is True or v is False:
            return repr(v)
        if v is Ellipsis:
            return 'ellipsis'
    return TARGET_DESCRIPTIONS.get(type(t), 'expression')


class ParserBase:
    """Token-stream helpers shared by all parts of the recursive-descent parser.

    The parser is split into mixins (statements, expressions, patterns,
    strings) that call one another through `self`; the methods they call
    across mixin boundaries are declared at the end of this class and
    implemented by the mixins (see boros.parser.Parser)."""

    toks: list[Token]
    pos: int
    tok: Token
    filename: str
    scope: Scope
    # set by `from __future__ import annotations`: annotations become strings
    future_annotations: bool = False
    loops: int
    future_ok: bool

    def __init__(self, toks: list[Token], filename: str, scope: Scope) -> None:
        """Start parsing `toks` (from `boros.lexer.tokenize`) at the first token.
        `scope` is the scope of the code being parsed; the parser switches to
        a new scope while inside a function, lambda or class body.  `loops`
        counts the loops around the current statement in the current
        function (for `break` and `continue`), and `future_ok` says whether
        a `from __future__` import may appear here."""
        self.toks = toks
        self.pos = 0
        self.tok = toks[0]
        self.filename = filename
        self.scope = scope
        self.loops = 0
        self.future_ok = False

    def error(self, msg: str | None = None, tok: Token | None = None,
              cls: type[SyntaxError] = SyntaxError) -> NoReturn:
        """Raise a SyntaxError (or `cls`, such as IndentationError) at `tok`
        (by default the current token), with its file name and line number.

        Without a message, the error describes the unexpected token."""
        if tok is None:
            tok = self.tok
        if msg is None:
            if tok[0] == 'EOF':
                msg = 'unexpected EOF while parsing'
            elif tok[0] == 'INDENT':
                msg = 'unexpected indent'
                cls = IndentationError
            elif tok[0] == 'NEWLINE' or tok[0] == 'DEDENT':
                msg = 'invalid syntax'
            else:
                msg = f'invalid syntax near {tok[1]!r}'
        raise syntax_error(msg, self.filename, tok[2], cls)

    def advance(self) -> Token:
        """Consume the current token and return it."""
        t: Token = self.tok
        self.pos += 1
        self.tok = self.toks[self.pos]
        return t

    def peek(self, k: int = 1) -> Token:
        """The token `k` places after the current one (EOF past the end)."""
        i: int = self.pos + k
        if i < len(self.toks):
            return self.toks[i]
        return self.toks[-1]

    def accept(self, v: str) -> bool:
        """Consume the current token if its text is `v`; return whether it was."""
        if self.tok[1] == v:
            self.advance()
            return True
        return False

    def expect(self, v: str) -> Token:
        """Consume the current token, which must have the text `v`."""
        if self.tok[1] != v:
            self.error(f"expected '{v}'")
        return self.advance()

    def expect_name(self) -> str:
        """Consume an identifier (a NAME that is not a keyword) and return it."""
        t: Token = self.tok
        if t[0] != 'NAME' or t[1] in KEYWORDS:
            self.error('expected a name')
        self.advance()
        return t[1]

    def mangle(self, name: str) -> str:
        """Apply private-name mangling: inside a class C, a name `__x` (not
        ending in two underscores) becomes `_C__x`."""
        cls: str | None = self.scope.classname if self.scope.kind != 'class' else self.scope.name
        if cls is not None and name[:2] == '__' and name[-2:] != '__' and '.' not in name:
            stripped: str = cls.lstrip('_')
            if stripped:
                return '_' + stripped + name
        return name

    def func_scope(self) -> Scope:
        """The scope that names bound by the current code belong to."""
        return self.scope

    def record_target(self, t: Expression, top: bool = True, verb: str = 'assign to') -> None:
        """Record the names bound by assignment target `t` in the current
        scope, rejecting expressions that cannot be assigned to (or deleted,
        when `verb` is 'delete') as CPython's parser does.  `top` is False
        for the elements of a tuple or list target, where a starred target
        may appear."""
        if type(t) is Name:
            self.scope.assigned.add(t.id)
            self.unuse(t.id)
        elif type(t) is Tuple or type(t) is List:
            self.record_elements(t.elts, verb)
        elif type(t) is Starred:
            if verb != 'assign to':
                self.error('cannot delete starred')
            if top:
                self.error('starred assignment target must be in a list or tuple')
            self.record_target(t.value, False, verb)
        elif type(t) is not Attribute and type(t) is not Subscript:
            self.error(f'cannot {verb} {target_description(t)}')

    def record_elements(self, elts: list[Expression], verb: str) -> None:
        """Record the elements of a tuple or list target, of which at most
        one may be starred."""
        stars: int = 0
        for e in elts:
            if type(e) is Starred:
                stars += 1
            self.record_target(e, False, verb)
        if stars > 1:
            self.error('multiple starred expressions in assignment')

    def check_target(self, t: Expression) -> None:
        """Reject an invalid comprehension target `t` without recording its
        names in the current scope (they belong to the comprehension)."""
        saved: set[str] = self.scope.assigned
        self.scope.assigned = set()
        try:
            self.record_target(t)
        finally:
            self.scope.assigned = saved

    def unuse(self, name: str) -> None:
        """`name` was parsed as an atom, which counts as a load of it (see
        ExpressionParser.atom), but it turned out not to be a load in the
        current scope (it is stored to, or belongs to a comprehension)."""
        self.scope.unloads.append(name)

    # -- implemented by the mixins ---------------------------------------------

    def suite(self) -> list[Statement]:
        """Parse an indented block or a one-line suite (StatementParser)."""
        raise NotImplementedError

    def parameters(self, closer: str, annotations: bool, scope: Scope) -> Arguments:
        """Parse a parameter list up to `closer` (StatementParser)."""
        raise NotImplementedError

    def looks_like_match(self) -> bool:
        """Is the current `match` token the start of a match statement? (PatternParser)"""
        raise NotImplementedError

    def match_stmt(self) -> Match:
        """Parse a match statement (PatternParser)."""
        raise NotImplementedError

    def test(self) -> Expression:
        """Parse a conditional expression or lambda (ExpressionParser)."""
        raise NotImplementedError

    def namedexpr_test(self) -> Expression:
        """Parse an expression that may be an assignment expression (ExpressionParser)."""
        raise NotImplementedError

    def testlist(self) -> Expression:
        """Parse a comma-separated expression list (ExpressionParser)."""
        raise NotImplementedError

    def testlist_star_expr(self) -> Expression:
        """Parse an expression list that may contain *starred items (ExpressionParser)."""
        raise NotImplementedError

    def target(self) -> Expression:
        """Parse one assignment target (ExpressionParser)."""
        raise NotImplementedError

    def target_list(self) -> Expression:
        """Parse a for-loop target list (ExpressionParser)."""
        raise NotImplementedError

    def exprlist(self, as_list: bool) -> list[Expression]:
        """Parse a comma-separated list of targets (ExpressionParser)."""
        raise NotImplementedError

    def call_args(self) -> tuple[list[Expression], list[Keyword]]:
        """Parse call arguments after the opening parenthesis (ExpressionParser)."""
        raise NotImplementedError

    def yield_expr(self) -> Expression:
        """Parse a yield or yield-from expression (ExpressionParser)."""
        raise NotImplementedError

    def strings(self) -> Expression:
        """Parse adjacent string literals, including f-strings (StringParser)."""
        raise NotImplementedError

