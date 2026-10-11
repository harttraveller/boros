"""Parsing of the `match` statement and its patterns.

A pattern looks like an expression but means something different: `Point(x=0, y=y)` checks that the
subject is a Point whose x is 0 and binds its y to the name `y`.  The grammar follows the precedence
of Python's own: `pattern_top` (an open sequence `a, b`), `pattern_as` (`p as name`), `pattern_or`
(`p | q`) and `pattern_closed` (everything else).  Every name a pattern captures is recorded as
assigned in the current scope, just like an assignment target.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..lexer import parse_number
from ..syntax import (
    Attribute,
    Const,
    Expression,
    JoinedStr,
    Match,
    MatchCase,
    Name,
    PAs,
    Pattern,
    PCapture,
    PClass,
    PMapping,
    POr,
    PSequence,
    PSingleton,
    PStar,
    PValue,
    PWildcard,
)
from .base import ParserBase

if TYPE_CHECKING:
    from ..core_types import Token

# the names that are matched by identity rather than captured
SINGLETONS: dict[str, bool | None] = {'None': None, 'True': True, 'False': False}


class PatternParser(ParserBase):
    """Parsing of the `match` statement and its patterns."""

    def looks_like_match(self) -> bool:
        """Is the current `match` token the start of a match statement?

        `match` is a soft keyword: it starts a match statement only when the
        logical line ends with a colon (otherwise it is an ordinary name, as
        in `match = re.match(...)`).  The lexer emits NEWLINE only outside
        brackets, so that colon is at bracket depth zero; the subject itself
        may contain colons (a lambda, a slice, a dict display)."""
        nxt: Token = self.peek()
        if nxt[0] == 'NEWLINE' or nxt[0] == 'EOF' or (nxt[0] == 'OP' and nxt[1] == '='):
            return False
        toks: list[Token] = self.toks
        i: int = self.pos + 1
        while toks[i][0] != 'NEWLINE' and toks[i][0] != 'EOF':
            i += 1
        last: Token = toks[i - 1]
        return i > self.pos + 2 and last[0] == 'OP' and last[1] == ':'

    def match_stmt(self) -> Match:
        """Parse a match statement: `match subject:` and an indented block of cases."""
        line: int = self.advance()[2]
        subject: Expression = self.testlist_star_expr()
        self.expect(':')
        if self.tok[0] != 'NEWLINE':
            self.error()
        self.advance()
        if self.tok[0] != 'INDENT':
            self.error('expected an indented block', None, IndentationError)
        self.advance()
        cases: list[MatchCase] = []
        while self.tok[0] != 'DEDENT':
            cases.append(self.match_case())
        self.advance()
        for case in cases[:-1]:
            if case.guard is None:
                self.check_reachable(case.pattern, ('NAME', 'case', case.line))
        return Match(line, subject, cases)

    def match_case(self) -> MatchCase:
        """Parse one `case pattern [if guard]: body` of a match statement."""
        if self.tok[1] != 'case':
            self.error("expected 'case'")
        line: int = self.advance()[2]
        pattern: Pattern = self.pattern_top()
        self.check_pattern(pattern, [], ('NAME', 'case', line))
        guard: Expression | None = None
        if self.accept('if'):
            guard = self.namedexpr_test()
        self.expect(':')
        return MatchCase(line, pattern, guard, self.suite())

    # -- compile-time checks of patterns ------------------------------------------

    def check_reachable(self, p: Pattern, tok: Token) -> None:
        """Reject an irrefutable pattern (a capture or the wildcard, possibly
        under `as` or as an alternative), which would make the cases or
        alternatives after it unreachable."""
        if type(p) is PAs:
            self.check_reachable(p.pattern, tok)
        elif type(p) is POr:
            for alt in p.patterns:
                self.check_reachable(alt, tok)
        elif type(p) is PCapture:
            self.error(f"name capture '{p.name}' makes remaining patterns unreachable", tok)
        elif type(p) is PWildcard:
            self.error('wildcard makes remaining patterns unreachable', tok)

    def check_pattern(self, p: Pattern, names: list[str], tok: Token) -> None:
        """CPython's compile-time checks of pattern p (of the case at token
        tok), appending the names it binds to `names`: a name may be bound
        only once."""
        if type(p) is POr:
            self.check_or_pattern(p, names, tok)
            return
        for sub in sub_patterns(p):
            self.check_pattern(sub, names, tok)
        name: str | None = bound_name(p)
        if name is not None:
            if name in names:
                self.error(f"multiple assignments to name '{name}' in pattern", tok)
            names.append(name)
        msg: str | None = pattern_shape_error(p)
        if msg is not None:
            self.error(msg, tok)

    def check_or_pattern(self, p: POr, names: list[str], tok: Token) -> None:
        """Check an or-pattern: only its last alternative may be irrefutable,
        and all the alternatives must bind the same names."""
        first: list[str] | None = None
        last: int = len(p.patterns) - 1
        for i, alt in enumerate(p.patterns):
            if i < last:
                self.check_reachable(alt, tok)
            bound: list[str] = []
            self.check_pattern(alt, bound, tok)
            if first is None:
                first = bound
            elif sorted(bound) != sorted(first):
                self.error('alternative patterns bind different names', tok)
        for x in first or []:
            if x in names:
                self.error(f"multiple assignments to name '{x}' in pattern", tok)
            names.append(x)

    def pattern_top(self) -> Pattern:
        """Parse the pattern of a case, which may be an open sequence `a, *rest`."""
        line: int = self.tok[2]
        p: Pattern = self.pattern_as()
        if self.tok[1] == ',':
            pats: list[Pattern] = [p]
            while self.accept(','):
                if self.tok[1] == ':' or self.tok[1] == 'if':
                    break
                pats.append(self.pattern_as())
            return PSequence(line, pats)
        return p

    def pattern_as(self) -> Pattern:
        """Parse `pattern as name` (or just the pattern)."""
        line: int = self.tok[2]
        p: Pattern = self.pattern_or()
        if self.accept('as'):
            return PAs(line, p, self.bind_capture(self.expect_name()))
        return p

    def pattern_or(self) -> Pattern:
        """Parse alternatives `p | q | ...` (or a single closed pattern)."""
        line: int = self.tok[2]
        p: Pattern = self.pattern_closed()
        if self.tok[1] == '|':
            pats: list[Pattern] = [p]
            while self.accept('|'):
                pats.append(self.pattern_closed())
            return POr(line, pats)
        return p

    def pattern_closed(self) -> Pattern:
        """Parse a closed pattern, choosing the kind by its first token."""
        t: Token = self.tok
        if t[0] == 'OP':
            return self.pattern_punctuation(t[1], t[2])
        if t[0] == 'NUMBER':
            return PValue(t[2], self.pattern_number())
        if t[0] == 'STRING':
            return PValue(t[2], self.strings())
        if t[0] == 'NAME':
            return self.pattern_name(t[1], t[2])
        self.error('invalid pattern')

    def pattern_punctuation(self, v: str, line: int) -> Pattern:
        """Parse a closed pattern that starts with the operator `v`: a group or
        sequence in () or [], a star pattern, a mapping or a negative number."""
        if v == '(' or v == '[':
            return self.pattern_group(v, line)
        if v == '*':
            return self.pattern_star(line)
        if v == '{':
            return self.pattern_mapping()
        if v == '-':
            return PValue(line, self.pattern_number())
        self.error('invalid pattern')

    def pattern_group(self, opener: str, line: int) -> Pattern:
        """Parse a parenthesized pattern or a sequence pattern in () or [].
        `(p)` is just p, while `(p,)` and `[p]` are sequence patterns."""
        close: str = ')' if opener == '(' else ']'
        self.advance()
        pats: list[Pattern] = []
        trailing: bool = False
        while self.tok[1] != close:
            pats.append(self.pattern_as())
            trailing = False
            if not self.accept(','):
                break
            trailing = True
        self.expect(close)
        if opener == '(' and len(pats) == 1 and not trailing:
            return pats[0]
        return PSequence(line, pats)

    def pattern_star(self, line: int) -> PStar:
        """Parse `*name` in a sequence pattern, which captures the remaining
        items (`*_` captures nothing)."""
        self.advance()
        name: str = self.expect_name()
        if name == '_':
            return PStar(line, None)
        return PStar(line, self.bind_capture(name))

    def pattern_name(self, v: str, line: int) -> Pattern:
        """Parse a closed pattern that starts with the name `v`: None, True or
        False, a dotted value such as `Color.RED`, a class pattern such as
        `Point(x, y)`, the wildcard `_` or a capture pattern."""
        self.advance()
        if v == 'None' or v == 'True' or v == 'False':
            return PSingleton(line, SINGLETONS[v])
        if self.tok[1] == '.' or self.tok[1] == '(':
            node: Expression = self.pattern_dotted_name(v, line)
            if self.tok[1] == '(':
                return self.pattern_class(node)
            return PValue(line, node)
        if v == '_':
            return PWildcard(line)
        return PCapture(line, self.bind_capture(v))

    def pattern_dotted_name(self, first: str, line: int) -> Expression:
        """Parse the rest of a dotted name `first.a.b` whose first name has
        been consumed, as a Name with Attribute lookups."""
        node: Expression = Name(line, self.mangle(first))
        while self.accept('.'):
            node = Attribute(line, node, self.expect_name())
        return node

    def bind_capture(self, name: str) -> str:
        """Mangle a name captured by a pattern and record it as assigned in
        the current scope."""
        name = self.mangle(name)
        self.scope.assigned.add(name)
        return name

    def pattern_number(self) -> Const:
        """Parse a number literal pattern: an optionally negated number, or a
        complex literal such as `-1 + 2j`."""
        line: int = self.tok[2]
        neg: bool = self.accept('-')
        if self.tok[0] != 'NUMBER':
            self.error('invalid pattern')
        value: int | float | complex = parse_number(self.advance()[1])
        if neg:
            value = -value
        if self.tok[1] == '+' or self.tok[1] == '-':
            if type(value) is complex:
                self.error('real number required in complex literal')
            op: str = self.advance()[1]
            if self.tok[0] != 'NUMBER':
                self.error()
            imag: int | float | complex = parse_number(self.advance()[1])
            if type(imag) is not complex:
                self.error('imaginary number required in complex literal')
            if op == '+':
                value = value + imag
            else:
                value = value - imag
        return Const(line, value)

    def pattern_mapping(self) -> PMapping:
        """Parse a mapping pattern `{key: pattern, ..., **rest}`."""
        line: int = self.advance()[2]
        keys: list[Expression] = []
        pats: list[Pattern] = []
        rest: str | None = None
        while self.tok[1] != '}':
            if self.accept('**'):
                rest = self.pattern_rest()
                break
            else:
                keys.append(self.pattern_mapping_key())
                self.expect(':')
                pats.append(self.pattern_as())
            if not self.accept(','):
                break
        self.expect('}')
        return PMapping(line, keys, pats, rest)

    def pattern_rest(self) -> str:
        """Parse the name of a `**rest` entry, which must be the last of a
        mapping pattern (and cannot be `**_`)."""
        if self.tok[1] == '_':
            self.error()
        rest: str = self.bind_capture(self.expect_name())
        self.accept(',')
        if self.tok[1] != '}':
            self.error()
        return rest

    def pattern_mapping_key(self) -> Expression:
        """Parse the key of a mapping pattern: a literal or a dotted name."""
        kt: Token = self.tok
        if kt[0] == 'NAME' and kt[1] not in ('None', 'True', 'False'):
            self.advance()
            return self.pattern_dotted_name(kt[1], kt[2])
        kp: Pattern = self.pattern_closed()
        if type(kp) is PSingleton:
            return Const(kt[2], kp.value)
        if type(kp) is PValue:
            return kp.value
        self.error('mapping pattern keys may only match literals and attribute lookups', kt)

    def pattern_class(self, cls: Expression) -> PClass:
        """Parse the arguments of a class pattern `Cls(p1, p2, name=p3)`:
        positional sub-patterns, then keyword sub-patterns."""
        line: int = self.advance()[2]
        pats: list[Pattern] = []
        kwd_names: list[str] = []
        kwd_pats: list[Pattern] = []
        while self.tok[1] != ')':
            if self.tok[0] == 'NAME' and self.peek()[1] == '=':
                kwd_names.append(self.advance()[1])
                self.advance()
                kwd_pats.append(self.pattern_as())
            else:
                pats.append(self.pattern_as())
            if not self.accept(','):
                break
        self.expect(')')
        return PClass(line, cls, pats, kwd_names, kwd_pats)


def sub_patterns(p: Pattern) -> list[Pattern]:
    """The patterns directly inside pattern p (other than an or-pattern)."""
    if type(p) is PSequence or type(p) is PMapping:
        return p.patterns
    if type(p) is PClass:
        return p.patterns + p.kwd_patterns
    if type(p) is PAs:
        return [p.pattern]
    return []


def bound_name(p: Pattern) -> str | None:
    """The name that pattern p itself binds, if any (not counting the names
    bound by the patterns inside it)."""
    if type(p) is PCapture or type(p) is PAs or type(p) is PStar:
        return p.name
    if type(p) is PMapping:
        return p.rest
    return None


def pattern_shape_error(p: Pattern) -> str | None:
    """The SyntaxError message for a pattern CPython rejects at compile
    time because of its own parts: several starred names in a sequence,
    a duplicate literal key or class keyword, or an f-string value."""
    if type(p) is PSequence and len([x for x in p.patterns if type(x) is PStar]) > 1:
        return 'multiple starred names in sequence pattern'
    if type(p) is PMapping:
        keys: list[Any] = []
        for k in p.keys:
            if type(k) is Const:
                if k.value in keys:
                    return f'mapping pattern checks duplicate key ({k.value!r})'
                keys.append(k.value)
    if type(p) is PClass:
        for i, k in enumerate(p.kwd_names):
            if k in p.kwd_names[:i]:
                return f'attribute name repeated in class pattern: {k}'
    if type(p) is PValue and type(p.value) is JoinedStr:
        return 'patterns may only match literals and attribute lookups'
    return None
