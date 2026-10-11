"""Parsing of string literals, including f-strings.

The lexer hands over each string literal undecoded, as a (prefix, body)
pair.  Here adjacent literals are concatenated ('a' 'b' is 'ab'), escapes
are decoded, and f-strings are split into literal text and replacement
fields.  The expression inside each replacement field is tokenized and
parsed by a fresh parser, so `f'{a + b!r:>10}'` becomes
JoinedStr([FormattedValue(BinOp(a, '+', b), 'r', JoinedStr([Const('>10')]))]).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..lexer import FIELD_SKIPS, decode_bytes, decode_string, skip_format_spec, syntax_error, tokenize
from ..syntax import Const, Expression, FormattedValue, JoinedStr
from .base import ParserBase

if TYPE_CHECKING:
    from ..core_types import Token


class StringParser(ParserBase):
    """Parsing of string literals, including f-strings."""

    def strings(self) -> Expression:
        """Parse one or more adjacent string literals into a single Const, or
        a JoinedStr when any of them is an f-string.  Bytes and str literals
        cannot be mixed.  A SyntaxError from decoding a literal (such as a
        malformed escape) is given the line of the literals."""
        line: int = self.tok[2]
        try:
            return self.string_literals()
        except SyntaxError as e:
            if e.lineno is not None:
                raise
            raise syntax_error(str(e.args[0]), self.filename, line) from None

    def string_literals(self) -> Expression:
        """The body of `strings`: parse and decode the literals."""
        line: int = self.tok[2]
        parts: list[Expression] = []
        has_f: bool = False
        is_bytes: bool | None = None
        while self.tok[0] == 'STRING':
            prefix, body = self.advance()[1]
            low: str = prefix.lower()
            raw: bool = 'r' in low
            b: bool = 'b' in low
            if is_bytes is None:
                is_bytes = b
            elif is_bytes != b:
                self.error('cannot mix bytes and nonbytes literals')
            if 'f' in low:
                has_f = True
                parts.extend(self.fstring(body, raw, line))
            elif b:
                parts.append(Const(line, decode_bytes(body, raw)))
            else:
                parts.append(Const(line, decode_string(body, raw)))
        if has_f:
            return JoinedStr(line, merge_literals(parts, line))
        return join_constants(parts, bool(is_bytes), line)

    def fstring(self, s: str, raw: bool, line: int) -> list[Expression]:
        """Split the body of an f-string into literal parts (Const) and
        replacement fields (FormattedValue).  Literal text is collected
        undecoded in `lit` and decoded when a field or the end is reached;
        '{{' and '}}' stand for single braces."""
        parts: list[Expression] = []
        lit: list[str] = []
        i: int = 0
        n: int = len(s)
        while i < n:
            c: str = s[i]
            if c == '\\' and not raw:
                i = take_escape(s, i, lit)
            elif c == '{' and s.startswith('{{', i):
                lit.append('{')
                i += 2
            elif c == '{':
                if lit:
                    parts.append(Const(line, decode_string(''.join(lit), raw)))
                    lit = []
                i = self.fstring_field(s, i + 1, raw, line, parts)
            elif c == '}' and s.startswith('}}', i):
                lit.append('}')
                i += 2
            elif c == '}':
                self.error("f-string: single '}' is not allowed")
            else:
                lit.append(c)
                i += 1
        if lit:
            parts.append(Const(line, decode_string(''.join(lit), raw)))
        return parts

    def fstring_field(self, s: str, i: int, raw: bool, line: int, parts: list[Expression]) -> int:
        """Parse the replacement field that starts at s[i], just after its '{':
        an expression, then optionally '=' (self-documenting, f'{x=}' shows
        'x=' and repr(x)), '!' and a conversion letter, and ':' and a format
        spec, which may itself contain replacement fields.  Appends the parts
        to `parts` and returns the index after the closing '}'."""
        start: int = i
        n: int = len(s)
        i = self.field_expression_end(s, i, line)
        text: str = s[start:i]
        if not text.strip():
            self.error('f-string: valid expression required before }')
        expr: Expression = self.sub_expression(text, line)
        conv: str | None = None
        spec: JoinedStr | None = None
        selfdoc: bool = s[i] == '='
        if selfdoc:
            i += 1
            while i < n and s[i] in ' \t\n':
                i += 1
            parts.append(Const(line, s[start:i]))
        if s[i:i + 1] == '!':
            conv, i = self.conversion(s, i + 1)
            selfdoc = False
        if s[i:i + 1] == ':':
            spec_end: int = skip_format_spec(s, i + 1, '', raw, line, self.filename) - 1
            spec = JoinedStr(line, self.fstring(s[i + 1:spec_end], raw, line))
            i = spec_end
        elif selfdoc:
            conv = 'r'
        if i >= n or s[i] != '}':
            self.error("f-string: expecting '}'")
        parts.append(FormattedValue(line, expr, conv, spec))
        return i + 1

    def conversion(self, s: str, i: int) -> tuple[str, int]:
        """Parse the conversion of a replacement field, which starts at s[i]
        just after the '!': 'r', 's' or 'a', which may be followed by
        whitespace.  Returns it and the index after it."""
        n: int = len(s)
        j: int = i
        while j < n and (s[j].isalnum() or s[j] == '_'):
            j += 1
        conv: str = s[i:j]
        if not conv:
            self.error('f-string: missing conversion character')
        if conv != 'r' and conv != 's' and conv != 'a':
            self.error(f"f-string: invalid conversion character {conv!r}: expected 's', 'r', or 'a'")
        while j < n and s[j] in ' \t\n':
            j += 1
        return conv, j

    def field_expression_end(self, s: str, i: int, line: int) -> int:
        """Find the end of the expression of a replacement field starting at
        s[i]: the first '}', '!', ':' or '=' outside brackets, strings and
        comments (see `ends_field_expression`)."""
        start: int = i
        n: int = len(s)
        depth: int = 0
        while i < n:
            c: str = s[i]
            if c in FIELD_SKIPS:
                i = FIELD_SKIPS[c](s, i, line, self.filename)
                continue
            if c == '(' or c == '[' or c == '{':
                depth += 1
            elif c == ')' or c == ']':
                depth -= 1
            elif c == '}':
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and ends_field_expression(s, i, start):
                break
            i += 1
        if i >= n:
            self.error("f-string: expecting '}'")
        return i

    def sub_expression(self, text: str, line: int) -> Expression:
        """Parse the expression of a replacement field with a new parser.  The
        text is wrapped in parentheses so that it may span lines, and token
        line numbers are shifted to the line of the f-string.  (The closing
        parenthesis goes on a line of its own, after any comment.)"""
        toks: list[Token] = tokenize('(' + text + '\n)', self.filename)
        toks = [(k, v, ln + line - 1) for (k, v, ln) in toks]
        p: ParserBase = type(self)(toks, self.filename, self.scope)
        e: Expression = p.testlist_star_expr()
        if p.tok[0] != 'NEWLINE':
            p.error()
        return e


def ends_field_expression(s: str, i: int, start: int) -> bool:
    """Does s[i], outside brackets, end the expression of a replacement field
    that starts at s[start]?  '!' starts a conversion, ':' a format spec and
    '=' a self-documenting field, unless they belong to '!=', '==', '<=',
    '>=' or a longer comparison."""
    c: str = s[i]
    if c == '!':
        return not s.startswith('!=', i)
    if c == ':':
        return True
    if c == '=':
        return not s.startswith('==', i) and (i == start or s[i - 1] not in '=!<>')
    return False


def take_escape(s: str, i: int, lit: list[str]) -> int:
    """Copy the backslash escape at s[i] of an f-string into the literal text
    `lit`, which is decoded later, and return the index after it.  Before a
    brace the backslash stays a literal backslash and the brace keeps its
    meaning; a \\N{NAME} escape is copied whole."""
    if s.startswith('\\N{', i):
        j: int = s.find('}', i)
        if j >= 0:
            lit.append(s[i:j + 1])
            return j + 1
    nxt: str = s[i + 1:i + 2]
    if nxt == '{' or nxt == '}':
        lit.append('\\\\')
        return i + 1
    lit.append(s[i:i + 2])
    return i + 2


def merge_literals(parts: list[Expression], line: int) -> list[Expression]:
    """The parts of an f-string with adjacent literal parts merged into one
    Const and empty literal parts dropped."""
    merged: list[Expression] = []
    for p in parts:
        if type(p) is not Const:
            merged.append(p)
            continue
        last: Expression | None = merged[-1] if merged else None
        if type(last) is Const:
            merged[-1] = Const(line, last.value + p.value)
        elif p.value != '':
            merged.append(p)
    return merged


def join_constants(parts: list[Expression], is_bytes: bool, line: int) -> Expression:
    """Concatenate adjacent plain (non-f) string or bytes literals, which
    are all Const nodes, into one Const."""
    if len(parts) == 1:
        return parts[0]
    values: list[Any] = [p.value for p in parts if type(p) is Const]
    if is_bytes:
        return Const(line, b''.join(values))
    return Const(line, ''.join(values))
