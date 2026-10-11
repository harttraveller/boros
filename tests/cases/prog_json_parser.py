"""A small JSON-like recursive descent parser with error reporting, plus a
pretty printer, round-tripped against the host json module."""
import json


class ParseError(Exception):
    def __init__(self, msg, pos, text):
        super().__init__(msg)
        self.pos = pos
        self.text = text

    def __str__(self):
        line = self.text.count("\n", 0, self.pos) + 1
        col = self.pos - (self.text.rfind("\n", 0, self.pos) + 1) + 1
        return "%s at line %d col %d" % (self.args[0], line, col)


ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}


class Parser:
    WS = " \t\r\n"

    def __init__(self, text):
        self.text = text
        self.i = 0

    def error(self, msg):
        raise ParseError(msg, self.i, self.text)

    def skip(self):
        t, n = self.text, len(self.text)
        while self.i < n and t[self.i] in self.WS:
            self.i += 1

    def peek(self):
        self.skip()
        return self.text[self.i] if self.i < len(self.text) else ""

    def expect(self, ch):
        if self.peek() != ch:
            self.error("expected %r" % ch)
        self.i += 1

    def parse(self):
        v = self.value()
        if self.peek():
            self.error("trailing data")
        return v

    def value(self):
        c = self.peek()
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c == '"':
            return self.string()
        if c == "-" or c.isdigit():
            return self.number()
        for word, val in (("true", True), ("false", False), ("null", None)):
            if self.text.startswith(word, self.i):
                self.i += len(word)
                return val
        if not c:
            self.error("unexpected end of input")
        self.error("unexpected character %r" % c)

    def obj(self):
        self.expect("{")
        out = {}
        if self.peek() == "}":
            self.i += 1
            return out
        while True:
            if self.peek() != '"':
                self.error("object keys must be strings")
            k = self.string()
            self.expect(":")
            out[k] = self.value()
            c = self.peek()
            self.i += 1
            if c == "}":
                return out
            if c != ",":
                self.i -= 1
                self.error("expected ',' or '}'")

    def arr(self):
        self.expect("[")
        out = []
        if self.peek() == "]":
            self.i += 1
            return out
        while True:
            out.append(self.value())
            c = self.peek()
            self.i += 1
            if c == "]":
                return out
            if c != ",":
                self.i -= 1
                self.error("expected ',' or ']'")

    def string(self):
        self.expect('"')
        buf = []
        t = self.text
        while True:
            if self.i >= len(t):
                self.error("unterminated string")
            c = t[self.i]
            self.i += 1
            if c == '"':
                return "".join(buf)
            if c == "\\":
                e = t[self.i]
                self.i += 1
                if e == "u":
                    code = t[self.i:self.i + 4]
                    try:
                        buf.append(chr(int(code, 16)))
                    except ValueError:
                        self.error("bad unicode escape %r" % code)
                    self.i += 4
                elif e in ESCAPES:
                    buf.append(ESCAPES[e])
                else:
                    self.error("bad escape \\%s" % e)
            else:
                buf.append(c)

    def number(self):
        start = self.i
        t = self.text
        if t[self.i] == "-":
            self.i += 1
        while self.i < len(t) and (t[self.i].isdigit() or t[self.i] in ".eE+-"):
            self.i += 1
        s = t[start:self.i]
        try:
            return float(s) if any(ch in s for ch in ".eE") else int(s)
        except ValueError:
            self.i = start
            self.error("bad number %r" % s)


def pretty(v, indent=0, step=2):
    pad = " " * indent
    inner = " " * (indent + step)
    if isinstance(v, dict):
        if not v:
            return "{}"
        items = [inner + quote(k) + ": " + pretty(x, indent + step) for k, x in sorted(v.items())]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(v, list):
        if not v:
            return "[]"
        if all(not isinstance(x, (list, dict)) for x in v):
            return "[" + ", ".join(pretty(x) for x in v) + "]"
        return "[\n" + ",\n".join(inner + pretty(x, indent + step) for x in v) + "\n" + pad + "]"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, str):
        return quote(v)
    return repr(v)


def quote(s):
    out = ['"']
    for ch in s:
        if ch == '"' or ch == "\\":
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20 or ord(ch) > 0x7E:
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


DOC = """
{
  "name": "boros", "version": [1, 2, 3], "ok": true, "nothing": null,
  "nested": {"pi": 3.25, "neg": -17, "exp": 1.5e3, "list": [{"a": 1}, {"b": [true, false]}, []]},
  "text": "line\\nbreak \\"quoted\\" tab\\t \\u00e9t\\u00e9 \\/slash",
  "empty": {}
}
"""

data = Parser(DOC).parse()
print(pretty(data))
assert data == json.loads(DOC), "mismatch with json module"
print("roundtrip:", Parser(pretty(data)).parse() == data)
print("host json agrees:", json.loads(pretty(data)) == data)

BAD = [
    '{"a": 1,}',
    '[1, 2',
    '{"a" 1}',
    '"abc',
    '[1, 2] x',
    '{1: 2}',
    '"\\q"',
    '"\\uZZZZ"',
    '-',
    '\n\n  @',
    '',
]
for text in BAD:
    try:
        Parser(text).parse()
        print("parsed?!", text)
    except ParseError as e:
        print("%-12r -> %s (pos=%d)" % (text, e, e.pos))

# statistics over the document
def walk(v, depth=0):
    yield depth, type(v).__name__
    if isinstance(v, dict):
        for x in v.values():
            yield from walk(x, depth + 1)
    elif isinstance(v, list):
        for x in v:
            yield from walk(x, depth + 1)


counts = {}
maxdepth = 0
for d, tname in walk(data):
    counts[tname] = counts.get(tname, 0) + 1
    maxdepth = max(maxdepth, d)
print(sorted(counts.items()), "maxdepth", maxdepth)
