"""Expression evaluator: regex tokenizer, Pratt parser with operator precedence
and associativity, an AST of small classes, variables/functions, and precise
error reporting with a caret under the offending column."""
import math
import operator
import re


class EvalError(Exception):
    """Base for all evaluator errors; carries the source column."""

    def __init__(self, message, col=None):
        super().__init__(message)
        self.col = col

    def render(self, src):
        if self.col is None:
            return "%s: %s" % (type(self).__name__, self)
        return "%s\n%s^\n%s: %s" % (src, " " * self.col, type(self).__name__, self)


class LexError(EvalError):
    pass


class SyntaxErr(EvalError):
    pass


class NameErr(EvalError):
    pass


class MathErr(EvalError):
    pass


TOKEN = re.compile(r"(?P<ws>\s+)|(?P<num>\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)|(?P<name>[a-zA-Z_]\w*)"
                   r"|(?P<op>\*\*|//|[-+*/%^(),=!])")


def tokenize(src):
    pos = 0
    out = []
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if m is None:
            raise LexError("unexpected character %r" % src[pos], pos)
        kind = m.lastgroup
        if kind != "ws":
            out.append((kind, m.group(), pos))
        pos = m.end()
    out.append(("eof", "", len(src)))
    return out


class Num:
    def __init__(self, v):
        self.v = v

    def eval(self, env):
        return self.v

    def __repr__(self):
        return repr(self.v)


class Var:
    def __init__(self, name, col):
        self.name, self.col = name, col

    def eval(self, env):
        try:
            return env[self.name]
        except KeyError:
            raise NameErr("unknown variable %r" % self.name, self.col) from None

    def __repr__(self):
        return self.name


class BinOp:
    FUNCS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv,
             "//": operator.floordiv, "%": operator.mod, "**": operator.pow, "^": operator.pow}

    def __init__(self, op, left, right, col):
        self.op, self.left, self.right, self.col = op, left, right, col

    def eval(self, env):
        a = self.left.eval(env)
        b = self.right.eval(env)
        try:
            return self.FUNCS[self.op](a, b)
        except ZeroDivisionError:
            raise MathErr("division by zero", self.col)
        except OverflowError as e:
            raise MathErr("overflow: %s" % e.args[1] if len(e.args) > 1 else "overflow", self.col)

    def __repr__(self):
        return "(%r %s %r)" % (self.left, self.op, self.right)


class Unary:
    def __init__(self, op, operand):
        self.op, self.operand = op, operand

    def eval(self, env):
        v = self.operand.eval(env)
        if self.op == "-":
            return -v
        if self.op == "!":
            return math.factorial(int(v))
        return +v

    def __repr__(self):
        return "(%s%r)" % (self.op, self.operand) if self.op != "!" else "(%r!)" % self.operand


class Call:
    def __init__(self, name, args, col):
        self.name, self.args, self.col = name, args, col

    def eval(self, env):
        f = env.get(self.name)
        if not callable(f):
            raise NameErr("%r is not a function" % self.name, self.col)
        vals = [a.eval(env) for a in self.args]
        try:
            return f(*vals)
        except (ValueError, TypeError) as e:
            raise MathErr("%s(): %s" % (self.name, e), self.col) from e

    def __repr__(self):
        return "%s(%s)" % (self.name, ", ".join(map(repr, self.args)))


class Assign:
    def __init__(self, name, value):
        self.name, self.value = name, value

    def eval(self, env):
        env[self.name] = v = self.value.eval(env)
        return v

    def __repr__(self):
        return "%s = %r" % (self.name, self.value)


# binding powers: (left bp, right bp); right-assoc ops have rbp < lbp
INFIX = {"+": (10, 11), "-": (10, 11), "*": (20, 21), "/": (20, 21), "//": (20, 21),
         "%": (20, 21), "**": (31, 30), "^": (31, 30)}
PREFIX_BP = 25
POSTFIX_BP = 40


class Parser:
    def __init__(self, src):
        self.toks = tokenize(src)
        self.i = 0

    @property
    def tok(self):
        return self.toks[self.i]

    def advance(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def expect(self, text):
        kind, val, col = self.tok
        if val != text:
            raise SyntaxErr("expected %r but found %s" % (text, repr(val) if val else "end of input"), col)
        return self.advance()

    def parse(self):
        if self.tok[0] == "name" and self.toks[self.i + 1][1] == "=":
            name = self.advance()[1]
            self.advance()
            node = Assign(name, self.expr(0))
        else:
            node = self.expr(0)
        if self.tok[0] != "eof":
            raise SyntaxErr("unexpected %r" % self.tok[1], self.tok[2])
        return node

    def expr(self, min_bp):
        kind, val, col = self.advance()
        if kind == "num":
            left = Num(float(val) if "." in val or "e" in val.lower() else int(val))
        elif kind == "name":
            if self.tok[1] == "(":
                self.advance()
                args = []
                if self.tok[1] != ")":
                    while True:
                        args.append(self.expr(0))
                        if self.tok[1] == ",":
                            self.advance()
                            continue
                        break
                self.expect(")")
                left = Call(val, args, col)
            else:
                left = Var(val, col)
        elif val in ("-", "+"):
            left = Unary(val, self.expr(PREFIX_BP))
        elif val == "(":
            left = self.expr(0)
            self.expect(")")
        else:
            raise SyntaxErr("unexpected %s" % (repr(val) if val else "end of input"), col)
        while True:
            kind, val, col = self.tok
            if val == "!":
                if POSTFIX_BP < min_bp:
                    break
                self.advance()
                left = Unary("!", left)
                continue
            if val not in INFIX:
                break
            lbp, rbp = INFIX[val]
            if lbp < min_bp:
                break
            self.advance()
            left = BinOp(val, left, self.expr(rbp), col)
        return left


def make_env():
    env = {"pi": math.pi, "e": math.e}
    env.update(sqrt=math.sqrt, max=max, min=min, abs=abs, log=math.log, hyp=lambda a, b: math.hypot(a, b))
    return env


def fmt(v):
    if isinstance(v, float):
        return "%.6g" % v
    return str(v)


env = make_env()
LINES = [
    "1 + 2 * 3",
    "(1 + 2) * 3",
    "2 ** 3 ** 2",
    "2 ^ 3 ^ 2 // 7",
    "-2 ** 2",
    "10 - 4 - 3",
    "7 // 2 + 7 % 2 + 7 / 2",
    "3! + 4!",
    "x = 5",
    "y = x * 2 + 1",
    "max(x, y, 3) - min(1, 2)",
    "hyp(3, 4)",
    "sqrt(2) * sqrt(2)",
    "1.5e3 + .5",
    "1 / 0",
    "zz + 1",
    "sqrt(-1)",
    "x(3)",
    "(1 + 2",
    "1 + * 2",
    "3 $ 4",
    "max()",
    "2 ** 10000.0",
    "",
]
for line in LINES:
    try:
        tree = Parser(line).parse()
        result = tree.eval(env)
        print("%-26s => %-12s %r" % (line, fmt(result), tree))
    except EvalError as err:
        print(err.render(line))
        if err.__cause__ is not None:
            print("   caused by", type(err.__cause__).__name__)
print(sorted(k for k, v in env.items() if not callable(v)))
print(issubclass(MathErr, EvalError), EvalError.__subclasses__() == [LexError, SyntaxErr, NameErr, MathErr])
