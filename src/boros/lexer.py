"""The tokenizer: turns source text into a list of tokens, and decodes literals.

Tokenizing is the first stage of running a program.  `tokenize` scans the
source with one big regular expression (`TOKEN_RE`), one token at a time,
and produces (kind, value, line) tuples for the parser:

- NAME, NUMBER and OP tokens carry their source text;
- a STRING token carries its (prefix, body) pair, still undecoded, because
  f-strings are split into literal parts and expressions by the parser;
- NEWLINE ends a logical line, and INDENT / DEDENT open and close indented
  blocks, which is how Python's significant whitespace reaches the parser;
- EOF ends the stream.

Newlines inside brackets, backslash continuations, blank lines and comments
produce no tokens.  The second half of the module turns the text of
literals into values: `decode_string`, `decode_bytes` and `parse_number`;
`decode_source` decodes source files given as bytes (PEP 263).
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .core_types import Token


def syntax_error(msg: str, filename: str, line: int, cls: type[SyntaxError] = SyntaxError) -> SyntaxError:
    """A SyntaxError (or IndentationError or TabError) that, like CPython's,
    carries the file name and line number in its `filename` and `lineno`
    attributes; str() of it is 'msg (filename, line N)'."""
    return cls(msg, (filename, line, None, None))


TAB_ERROR: str = 'inconsistent use of tabs and spaces in indentation'
"""The message of a TabError."""

# One alternative per kind of lexeme.  The upper-case groups are named
# after the token kinds they produce; the lower-case ones produce no token
# of their own.  Whitespace after a number, name or operator is matched
# along with it, which saves a trip around the tokenizer loop for most of
# the spaces in a program.  For a string literal only the prefix and the
# opening quote are matched here: the body is found by `string_token`.
TOKEN_RE: re.Pattern[str] = re.compile(r'''
 (?P<ws>[ \t\f]+)
|(?P<comment>\#[^\n]*)
|(?P<nl>\n)
|(?P<cont>\\\n)
|(?P<STRING>(?:[rR][bBfF]?|[bBfF][rR]?|[uU])?(?:\'\'\'|"""|\'|"))
|(?:(?P<NUMBER>0[xX](?:_?[0-9a-fA-F])+|0[bB](?:_?[01])+|0[oO](?:_?[0-7])+
    |(?:\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)?)?|\.\d(?:_?\d)*)(?:[eE][+-]?\d(?:_?\d)*)?[jJ]?)
  |(?P<NAME>[^\W\d]\w*)
  |(?P<OP>\*\*=|//=|>>=|<<=|->|\.\.\.|:=|\*\*|//|<<|>>|<=|>=|==|!=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|@=
    |[-+*/%&|^~<>()\[\]{},:;.=@!])
 )[ \t\f]*
''', re.VERBOSE)


# the indentation at the start of a line
INDENT_RE: re.Pattern[str] = re.compile(r'[ \t\f]*')


# The body of a (non-f) string literal up to and including its closing
# quote, for each kind of opening quote.
STRING_BODY: dict[str, re.Pattern[str]] = {
    "'": re.compile(r"(?:[^'\\\n]|\\.)*'", re.DOTALL),
    '"': re.compile(r'(?:[^"\\\n]|\\.)*"', re.DOTALL),
    "'''": re.compile(r"(?:[^'\\]|\\.|'(?!''))*'''", re.DOTALL),
    '"""': re.compile(r'(?:[^"\\]|\\.|"(?!""))*"""', re.DOTALL),
}


# brackets, which join the physical lines between them into one logical line
OPEN_BRACKETS: dict[str, int] = {'(': 1, '[': 1, '{': 1}


CLOSE_BRACKETS: dict[str, int] = {')': 1, ']': 1, '}': 1}


# -- tokenizing ------------------------------------------------------------------

def tokenize(src: str, filename: str = '<string>') -> list[Token]:
    """Turn source text into a list of (kind, value, line) tuples.

    Kinds are NAME, NUMBER, STRING, OP, NEWLINE, INDENT, DEDENT and EOF.
    The value of a STRING token is a (prefix, body) pair.  `depth` counts
    the open brackets: inside brackets a newline is just whitespace, while
    a newline at depth zero ends the logical line (NEWLINE), and then the
    indentation of the next one is examined by `start_logical_line`."""
    src = src.replace('\r\n', '\n').replace('\r', '\n')  # universal newlines
    toks: list[Token] = []
    append: Callable[[Token], None] = toks.append
    indents: list[int] = [0]  # indentation columns of the open blocks
    alts: list[int] = [0]  # the same with tabs counted as one column (see indent_tokens)
    n: int = len(src)
    depth: int = 0
    match: Callable[[str, int], re.Match[str] | None] = TOKEN_RE.match
    pos: int
    line: int
    pos, line = start_logical_line(src, 0, 1, indents, alts, toks, filename)
    while pos < n:
        m: re.Match[str] | None = match(src, pos)
        if m is None:
            raise syntax_error(f'invalid character {src[pos]!r}', filename, line)
        kind: str | None = m.lastgroup
        pos = m.end()
        if kind == 'OP':
            text: str = m.group('OP')
            if text in OPEN_BRACKETS:
                depth += 1
            elif text in CLOSE_BRACKETS and depth > 0:
                depth -= 1
            append(('OP', text, line))
        elif kind == 'NAME' or kind == 'NUMBER':
            append((kind, m.group(kind), line))
        elif kind == 'ws' or kind == 'comment':
            pass
        elif kind == 'nl' and depth == 0:
            append(('NEWLINE', '', line))
            pos, line = start_logical_line(src, pos, line + 1, indents, alts, toks, filename)
        elif kind == 'STRING':
            pos, line = string_token(src, pos, m.group(), line, filename, toks)
        else:  # a newline inside brackets, or a backslash continuation
            line += 1
    end_tokens(toks, indents, line)
    return toks if src.isascii() else normalize_names(toks)


def normalize_names(toks: list[Token]) -> list[Token]:
    """Put the non-ASCII identifiers among the tokens in NFKC normal form,
    in which PEP 3131 compares identifiers (where, for example, the
    ligature U+FB01 is the letters 'fi')."""
    for i, t in enumerate(toks):
        if t[0] == 'NAME' and not t[1].isascii():
            toks[i] = ('NAME', unicodedata.normalize('NFKC', t[1]), t[2])
    return toks


def start_logical_line(src: str, pos: int, line: int, indents: list[int], alts: list[int], toks: list[Token],
                       filename: str) -> tuple[int, int]:
    """Begin a logical line at `pos`, which is at the start of a physical line.

    Blank lines, comment-only lines and lines holding only a backslash
    continuation are skipped.  The indentation of the first real line is
    then compared with the open blocks (see `indent_tokens`).  Returns the
    position of the line's first token and its line number; the position is
    len(src) when the source ends first."""
    n: int = len(src)
    while True:
        m: re.Match[str] | None = INDENT_RE.match(src, pos)  # always matches, possibly the empty string
        indent: str = m.group() if m is not None else ''
        pos += len(indent)
        if pos >= n:
            return pos, line
        c: str = src[pos]
        if c == '\n':
            pos += 1
        elif c == '#':
            end: int = src.find('\n', pos)
            if end < 0:
                return n, line
            pos = end + 1
        elif src.startswith('\\\n', pos):
            pos += 2
        else:
            break
        line += 1
    col: int = len(indent)
    alt: int = col
    if '\t' in indent or '\f' in indent:
        col, alt = tab_column(indent)
    if col != indents[-1] or alt != alts[-1]:
        indent_tokens(col, alt, line, indents, alts, toks, filename)
    return pos, line


def tab_column(indent: str) -> tuple[int, int]:
    """The column reached by an indentation that contains tabs or form
    feeds: a tab advances to the next multiple of 8, a form feed resets the
    column to 0 and any other character advances by one.  Returned with the
    column reached when tabs count as one column, which CPython uses to
    detect inconsistent mixing of tabs and spaces."""
    col: int = 0
    alt: int = 0
    for ch in indent:
        if ch == '\t':
            col = (col // 8 + 1) * 8
            alt += 1
        elif ch == '\f':
            col = 0
            alt = 0
        else:
            col += 1
            alt += 1
    return col, alt


def indent_tokens(col: int, alt: int, line: int, indents: list[int], alts: list[int], toks: list[Token],
                  filename: str) -> None:
    """Emit the INDENT or DEDENT tokens for a logical line indented to `col`.

    `indents` is the stack of the open blocks' indentation columns.  A
    deeper line opens a block (one INDENT); a shallower one closes blocks
    (one DEDENT each) and must line up exactly with an enclosing block.
    `alt` and `alts` are the same columns with tabs counted as one column:
    they must compare the same way, or the indentation depends on the tab
    size and the error is a TabError, as in CPython."""
    if col > indents[-1]:
        if alt <= alts[-1]:
            raise syntax_error(TAB_ERROR, filename, line, TabError)
        indents.append(col)
        alts.append(alt)
        toks.append(('INDENT', '', line))
        return
    while col < indents[-1]:
        indents.pop()
        alts.pop()
        toks.append(('DEDENT', '', line))
    if col != indents[-1]:
        raise syntax_error('unindent does not match any outer indentation level', filename, line, IndentationError)
    if alt != alts[-1]:
        raise syntax_error(TAB_ERROR, filename, line, TabError)


def end_tokens(toks: list[Token], indents: list[int], line: int) -> None:
    """Finish the token list at the end of the source: end the last logical
    line, close every open block and add the EOF token."""
    if toks and toks[-1][0] != 'NEWLINE' and toks[-1][0] != 'DEDENT':
        toks.append(('NEWLINE', '', line))
    while len(indents) > 1:
        indents.pop()
        toks.append(('DEDENT', '', line))
    toks.append(('EOF', '', line))


def string_token(src: str, pos: int, opener: str, line: int, filename: str, toks: list[Token]) -> tuple[int, int]:
    """Read a string literal whose prefix and opening quote (`opener`) end at `pos`.

    Appends a STRING token holding (prefix, body), where the body is the raw
    text between the quotes, and returns the position after the closing
    quote together with the line the literal ends on."""
    quote: str = opener.lstrip('rRbBfFuU')
    prefix: str = opener[:len(opener) - len(quote)]
    low: str = prefix.lower()
    if 'f' in low:
        end: int = scan_fstring(src, pos, quote, 'r' in low, line, filename)
        body: str = src[pos:end]
        after: int = end + len(quote)
    else:
        m: re.Match[str] | None = STRING_BODY[quote].match(src, pos)
        if m is None:
            raise syntax_error('unterminated string literal', filename, line)
        body = src[pos:m.end() - len(quote)]
        after = m.end()
    toks.append(('STRING', (prefix, body), line))
    return after, line + body.count('\n')


# -- finding the end of an f-string ------------------------------------------------
#
# An f-string body alternates between literal text and replacement fields.
# A field has an expression part, in which brackets nest, quotes start
# nested strings (possibly f-strings themselves) and '#' starts a comment
# (PEP 701), and after a ':' at bracket depth zero a format spec, which is
# literal text again apart from nested replacement fields.

def scan_fstring(src: str, pos: int, quote: str, raw: bool, line: int, filename: str = '<string>') -> int:
    """Find the end of an f-string body starting at pos: the index of its
    closing quote.  Replacement fields may contain nested strings
    (including nested f-strings), so they are skipped as a whole."""
    n: int = len(src)
    q0: str = quote[0]
    i: int = pos
    while i < n:
        c: str = src[i]
        if c == q0 and src.startswith(quote, i):
            return i
        if c == '\\':
            i = skip_fstring_escape(src, i, raw)
        elif c == '{':
            if src.startswith('{{', i):
                i += 2  # an escaped brace
            else:
                i = skip_replacement_field(src, i + 1, quote, raw, line, filename)
        elif c == '\n' and len(quote) == 1:
            break
        else:
            i += 1
    raise syntax_error('unterminated f-string literal', filename, line)


def skip_fstring_escape(src: str, i: int, raw: bool) -> int:
    """Skip the backslash at src[i] in the literal text of an f-string.

    A brace after a backslash keeps its meaning, so only the backslash is
    skipped; the braces of a \\N{NAME} escape are not a replacement field."""
    nxt: str = src[i + 1:i + 2]
    if nxt == '{' or nxt == '}':
        return i + 1
    if not raw and nxt == 'N' and src.startswith('{', i + 2):
        end: int = src.find('}', i)
        if end >= 0:
            return end + 1
    return i + 2


def skip_replacement_field(src: str, i: int, quote: str, raw: bool, line: int, filename: str) -> int:
    """Skip an f-string replacement field whose opening brace is just before
    src[i], returning the index after the brace that closes it.  Strings and
    comments in the field's expression are skipped whole, so that the
    brackets and quotes inside them do not count; a ':' outside brackets
    starts the format spec (see `skip_format_spec`).  `quote` is the quote
    of the enclosing f-string ('' when it is not known)."""
    n: int = len(src)
    depth: int = 0
    while i < n:
        c: str = src[i]
        if c in FIELD_SKIPS:
            i = FIELD_SKIPS[c](src, i, line, filename)
            continue
        if c in OPEN_BRACKETS:
            depth += 1
        elif c in CLOSE_BRACKETS:
            if depth == 0:  # the '}' closing the field (or a stray bracket, which the parser rejects)
                return i + 1
            depth -= 1
        elif c == ':' and depth == 0:
            return skip_format_spec(src, i + 1, quote, raw, line, filename)
        i += 1
    raise syntax_error('unterminated f-string literal', filename, line)


def skip_format_spec(src: str, i: int, quote: str, raw: bool, line: int, filename: str) -> int:
    """Skip the format spec of a replacement field, which starts at src[i],
    returning the index after the '}' that closes the field.  The spec is
    literal text ('#', quotes and brackets in it are ordinary characters)
    except for nested replacement fields such as the {w} of f'{x:{w}}'.
    It cannot contain the f-string's closing quote, nor a newline in a
    single-quoted f-string."""
    n: int = len(src)
    while i < n:
        c: str = src[i]
        if c == '}':
            return i + 1
        if c == '{':
            i = skip_replacement_field(src, i + 1, quote, raw, line, filename)
            continue
        if c == '\\':
            i = skip_fstring_escape(src, i, raw)
            continue
        if (c == '\n' and len(quote) == 1) or (quote and src.startswith(quote, i)):
            break
        i += 1
    raise syntax_error("f-string: expecting '}'", filename, line)


def skip_field_comment(src: str, i: int, line: int, filename: str) -> int:
    """Skip a '#' comment in the expression of an f-string replacement
    field, up to (not including) the end of its line."""
    end: int = src.find('\n', i)
    if end < 0:
        raise syntax_error("f-string: expecting '}'", filename, line)
    return end


# The only prefixes a string literal can have (in lower case); a letter
# before a quote that does not form one of these is part of a name or
# keyword, as in `x if"a" else y`.
STRING_PREFIXES: dict[str, int] = {'': 1, 'r': 1, 'u': 1, 'b': 1, 'br': 1, 'rb': 1, 'f': 1, 'fr': 1, 'rf': 1}


def skip_nested_string(src: str, i: int, line: int, filename: str = '<string>') -> int:
    """Skip a string literal nested in an f-string replacement field.  src[i]
    is its opening quote (its prefix letters, if any, come just before);
    returns the index after its closing quote."""
    c: str = src[i]
    j: int = i
    while j > 0 and (src[j - 1].isalnum() or src[j - 1] == '_'):
        j -= 1
    prefix: str = src[j:i].lower()
    if prefix not in STRING_PREFIXES:
        prefix = ''
    q: str = c * 3 if src.startswith(c * 3, i) else c
    if 'f' in prefix:
        return scan_fstring(src, i + len(q), q, 'r' in prefix, line, filename) + len(q)
    m: re.Match[str] | None = STRING_BODY[q].match(src, i + len(q))
    if m is None:
        raise syntax_error('unterminated string literal', filename, line)
    return m.end()


# What skip_replacement_field does with a quote (a nested string) or a '#'
# (a comment) in the expression of a replacement field.
FIELD_SKIPS: dict[str, Callable[[str, int, int, str], int]] = {
    "'": skip_nested_string, '"': skip_nested_string, '#': skip_field_comment,
}


# -- decoding literals -----------------------------------------------------------

ESCAPE_RE: re.Pattern[str] = re.compile(
    r'\\(\n|[\\\'"abfnrtv]|[0-7]{1,3}|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|N\{[^}]*\}|.)', re.DOTALL)


SIMPLE_ESCAPES: dict[str, str] = {'\n': '', '\\': '\\', "'": "'", '"': '"', 'a': '\a', 'b': '\b',
                                  'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v'}


# The errors for \x, \u, \U and \N escapes that are cut short.
TRUNCATED_ESCAPES: dict[str, str] = {'x': 'truncated \\xXX escape', 'u': 'truncated \\uXXXX escape',
                                     'U': 'truncated \\UXXXXXXXX escape', 'N': 'malformed \\N character escape'}


def _escape(m: re.Match[str]) -> str:
    """The character a backslash escape in a str literal stands for (an
    unknown escape such as \\q stays as it is).  A malformed \\x, \\u, \\U
    or \\N escape is a SyntaxError (without a location: the parser adds it)."""
    e: str = m.group(1)
    r: str | None = SIMPLE_ESCAPES.get(e)
    if r is not None:
        return r
    c: str = e[0]
    if c in '01234567':
        return chr(int(e, 8))
    if len(e) > 1:
        if c == 'x' or c == 'u' or c == 'U':
            return code_point_char(int(e[1:], 16))
        if c == 'N':
            return named_char(e[2:-1])
    if c in TRUNCATED_ESCAPES:
        raise SyntaxError(f'(unicode error) {TRUNCATED_ESCAPES[c]}')
    return '\\' + e


def code_point_char(v: int) -> str:
    """The character of a \\x, \\u or \\U escape with code point v."""
    if v > 0x10FFFF:
        raise SyntaxError('(unicode error) illegal Unicode character')
    return chr(v)


def named_char(name: str) -> str:
    """The character of a \\N{name} escape."""
    try:
        return unicodedata.lookup(name)
    except KeyError:
        raise SyntaxError('(unicode error) unknown Unicode character name') from None


def _bytes_escape(m: re.Match[str]) -> str:
    """Like `_escape`, for a bytes literal, where \\u, \\U and \\N are not
    escapes and an octal escape keeps only the low 8 bits of its value."""
    e: str = m.group(1)
    c: str = e[0]
    if c == 'u' or c == 'U' or c == 'N':
        return '\\' + e
    if c in '01234567':
        return chr(int(e, 8) & 0xFF)
    if c == 'x' and len(e) == 1:
        raise SyntaxError('(value error) invalid \\x escape')
    return _escape(m)


def decode_string(body: str, raw: bool) -> str:
    """The value of a str literal with the given body (the text between the quotes)."""
    if raw or '\\' not in body:
        return body
    return ESCAPE_RE.sub(_escape, body)


def decode_bytes(body: str, raw: bool) -> bytes:
    """The value of a bytes literal with the given body, which may contain
    only ASCII characters."""
    if not body.isascii():
        raise SyntaxError('bytes can only contain ASCII literal characters')
    if not raw and '\\' in body:
        body = ESCAPE_RE.sub(_bytes_escape, body)
    return body.encode('latin-1')


def parse_number(s: str) -> int | float | complex:
    """The value of a NUMBER token: an int (decimal, hex, octal or binary,
    with optional underscores), a float or an imaginary number."""
    last: str = s[-1]
    if last == 'j' or last == 'J':
        return complex(0, float(s[:-1]))
    if len(s) > 1 and s[0] == '0' and s[1] in 'xXoObB':
        return int(s, 0)
    if '.' in s or 'e' in s or 'E' in s:
        return float(s)
    return int(s, 0)


# -- source encodings ----------------------------------------------------------------

CODING_RE: re.Pattern[str] = re.compile(r'^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)')
"""A PEP 263 coding declaration, such as `# -*- coding: latin-1 -*-`."""


def decode_source(data: bytes) -> str:
    """Decode the bytes of a source file (or bytes given to exec(), eval()
    or compile()) as PEP 263 says: UTF-8 after a UTF-8 byte order mark;
    otherwise in the encoding named by a coding declaration in a comment on
    the first line, or on the second line after a comment or blank first
    line; otherwise UTF-8."""
    enc: str = 'utf-8'
    if data[:3] == b'\xef\xbb\xbf':
        data = data[3:]
    else:
        for ln in data.split(b'\n', 2)[:2]:
            m: re.Match[str] | None = CODING_RE.match(ln.decode('latin-1'))
            if m is not None:
                enc = m.group(1)
                break
            if ln.strip() and ln.lstrip()[:1] != b'#':
                break
    try:
        return data.decode(enc)
    except LookupError:
        raise SyntaxError(f'unknown encoding: {enc}') from None
    except UnicodeDecodeError as e:
        raise SyntaxError(f'(unicode error) {e}') from None
