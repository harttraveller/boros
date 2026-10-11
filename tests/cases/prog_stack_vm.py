"""A tiny compiler from a toy language to bytecode, and a stack VM that runs it."""
import re
from collections import namedtuple


class Opcode(int):
    """An int subclass naming a VM opcode (a hand-rolled IntEnum)."""
    by_name = {}
    by_value = {}

    def __new__(cls, name, value):
        self = super().__new__(cls, value)
        self.name = name
        cls.by_name[name] = self
        cls.by_value[value] = self
        return self

    def __repr__(self):
        return "<Op.%s: %d>" % (self.name, int(self))

    def __str__(self):
        return "Op." + self.name


class OpTable:
    def __init__(self, names):
        for i, n in enumerate(names.split(), 1):
            setattr(self, n, Opcode(n, i))

    def __call__(self, value):
        return Opcode.by_value[value]

    def __getitem__(self, name):
        return Opcode.by_name[name]

    def __iter__(self):
        return iter(sorted(Opcode.by_value.values()))

    def __len__(self):
        return len(Opcode.by_value)


Op = OpTable("PUSH LOAD STORE ADD SUB MUL DIV MOD LT EQ JMP JZ PRINT CALL RET HALT")


class Kind:
    members = {}

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Kind.%s" % self.value.upper()


for _k in ("num", "name", "op", "kw"):
    setattr(Kind, _k.upper(), Kind(_k))
    Kind.members[_k] = getattr(Kind, _k.upper())


Instr = namedtuple("Instr", "op arg")
Token = namedtuple("Token", ["kind", "text", "line"])

KEYWORDS = {"while", "do", "end", "print", "if", "then", "else", "def", "return"}
TOKEN_RE = re.compile(r"\s*(?:(\d+)|([A-Za-z_]\w*)|(==|[-+*/%<=(),;]))")


class VMError(Exception):
    pass


def lex(src):
    toks = []
    for lineno, line in enumerate(src.splitlines(), 1):
        pos = 0
        line = line.split("#")[0].rstrip()
        while pos < len(line):
            m = TOKEN_RE.match(line, pos)
            if not m:
                raise SyntaxError("bad char %r on line %d" % (line[pos:].strip()[0], lineno))
            num, name, op = m.groups()
            if num:
                toks.append(Token(Kind.NUM, num, lineno))
            elif name:
                toks.append(Token(Kind.KW if name in KEYWORDS else Kind.NAME, name, lineno))
            else:
                toks.append(Token(Kind.OP, op, lineno))
            pos = m.end()
    return toks


class Compiler:
    PREC = {"<": 1, "==": 1, "+": 2, "-": 2, "*": 3, "/": 3, "%": 3}
    OPS = {"+": Op.ADD, "-": Op.SUB, "*": Op.MUL, "/": Op.DIV, "%": Op.MOD, "<": Op.LT, "==": Op.EQ}

    def __init__(self, toks):
        self.toks = toks
        self.i = 0
        self.code = []
        self.funcs = {}

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self, text=None):
        t = self.peek()
        if t is None or (text is not None and t.text != text):
            raise SyntaxError("expected %r got %r" % (text, t.text if t else "EOF"))
        self.i += 1
        return t

    def emit(self, op, arg=None):
        self.code.append(Instr(op, arg))
        return len(self.code) - 1

    def program(self):
        while self.peek() is not None:
            self.statement()
        self.emit(Op.HALT)
        return self.code

    def block(self, *terminators):
        while self.peek().text not in terminators:
            self.statement()

    def statement(self):
        t = self.peek()
        match t:
            case Token(kind=Kind.KW, text="print"):
                self.take()
                self.expr()
                self.emit(Op.PRINT)
            case Token(kind=Kind.KW, text="while"):
                self.take()
                top = len(self.code)
                self.expr()
                jz = self.emit(Op.JZ, None)
                self.take("do")
                self.block("end")
                self.take("end")
                self.emit(Op.JMP, top)
                self.code[jz] = self.code[jz]._replace(arg=len(self.code))
            case Token(kind=Kind.KW, text="if"):
                self.take()
                self.expr()
                jz = self.emit(Op.JZ, None)
                self.take("then")
                self.block("else", "end")
                if self.peek().text == "else":
                    self.take()
                    jmp = self.emit(Op.JMP, None)
                    self.code[jz] = Instr(Op.JZ, len(self.code))
                    self.block("end")
                    self.code[jmp] = Instr(Op.JMP, len(self.code))
                else:
                    self.code[jz] = Instr(Op.JZ, len(self.code))
                self.take("end")
            case Token(kind=Kind.KW, text="def"):
                self.take()
                name = self.take().text
                self.take("(")
                param = self.take().text
                self.take(")")
                skip = self.emit(Op.JMP, None)
                self.funcs[name] = (len(self.code), param)
                self.block("end")
                self.take("end")
                self.emit(Op.PUSH, 0)
                self.emit(Op.RET)
                self.code[skip] = Instr(Op.JMP, len(self.code))
            case Token(kind=Kind.KW, text="return"):
                self.take()
                self.expr()
                self.emit(Op.RET)
            case Token(kind=Kind.NAME, text=name):
                self.take()
                self.take("=")
                self.expr()
                self.emit(Op.STORE, name)
            case _:
                raise SyntaxError("unexpected %r on line %d" % (t.text, t.line))
        if self.peek() is not None and self.peek().text == ";":
            self.take()

    def expr(self, minprec=1):
        self.atom()
        while True:
            t = self.peek()
            if t is None or t.kind is not Kind.OP or t.text not in self.PREC:
                return
            p = self.PREC[t.text]
            if p < minprec:
                return
            self.take()
            self.expr(p + 1)
            self.emit(self.OPS[t.text])

    def atom(self):
        t = self.take()
        if t.kind == Kind.NUM:
            self.emit(Op.PUSH, int(t.text))
        elif t.kind == Kind.NAME:
            if self.peek() is not None and self.peek().text == "(":
                self.take("(")
                self.expr()
                self.take(")")
                if t.text not in self.funcs:
                    raise SyntaxError("unknown function %s" % t.text)
                self.emit(Op.CALL, t.text)
            else:
                self.emit(Op.LOAD, t.text)
        elif t.text == "(":
            self.expr()
            self.take(")")
        else:
            raise SyntaxError("bad atom %r" % t.text)


class VM:
    def __init__(self, code, funcs, limit=100000):
        self.code = code
        self.funcs = funcs
        self.limit = limit
        self.out = []

    def run(self):
        stack = []
        frames = [({}, None)]
        pc = 0
        steps = 0
        binops = {
            Op.ADD: lambda a, b: a + b,
            Op.SUB: lambda a, b: a - b,
            Op.MUL: lambda a, b: a * b,
            Op.LT: lambda a, b: int(a < b),
            Op.EQ: lambda a, b: int(a == b),
        }
        while True:
            steps += 1
            if steps > self.limit:
                raise VMError("step limit exceeded at pc=%d" % pc)
            op, arg = self.code[pc]
            pc += 1
            if op in binops:
                b = stack.pop()
                a = stack.pop()
                stack.append(binops[op](a, b))
            elif op is Op.PUSH:
                stack.append(arg)
            elif op is Op.LOAD:
                env = frames[-1][0]
                if arg not in env:
                    raise VMError("undefined variable %r" % arg)
                stack.append(env[arg])
            elif op is Op.STORE:
                frames[-1][0][arg] = stack.pop()
            elif op in (Op.DIV, Op.MOD):
                b = stack.pop()
                a = stack.pop()
                try:
                    stack.append(a // b if op == Op.DIV else a % b)
                except ZeroDivisionError as e:
                    raise VMError("division by zero at pc=%d" % (pc - 1)) from e
            elif op is Op.JMP:
                pc = arg
            elif op is Op.JZ:
                if not stack.pop():
                    pc = arg
            elif op is Op.PRINT:
                self.out.append(stack.pop())
            elif op is Op.CALL:
                entry, param = self.funcs[arg]
                frames.append(({param: stack.pop()}, pc))
                pc = entry
            elif op is Op.RET:
                _, pc = frames.pop()
            elif op is Op.HALT:
                return steps
            else:
                raise VMError("bad opcode %r" % (op,))


def run(src, limit=100000):
    comp = Compiler(lex(src))
    code = comp.program()
    vm = VM(code, comp.funcs, limit)
    steps = vm.run()
    return vm.out, steps, len(code)


PROGRAMS = {
    "count": "i = 0\nwhile i < 5 do print i; i = i + 1 end",
    "fact": """
def fact(n)
  if n < 2 then return 1 else return n * fact(n - 1) end
end
print fact(10)
""",
    "collatz": """
n = 27; steps = 0
while 1 - (n == 1) do
  if n % 2 == 0 then n = n / 2 else n = 3 * n + 1 end
  steps = steps + 1
end
print steps
""",
    "prec": "print 2 + 3 * 4 - 10 / 3; print (2 + 3) * 4; print 7 % 3 * 2",
    "divzero": "x = 0\nprint 10 / x",
    "undef": "print y + 1",
    "loop": "while 1 do x = 1 end",
    "syntax": "print 1 +",
    "badchar": "x = 1 $ 2",
}

for name, src in PROGRAMS.items():
    try:
        out, steps, size = run(src, limit=3000)
        print("%-8s out=%s steps=%d size=%d" % (name, out, steps, size))
    except VMError as e:
        cause = type(e.__cause__).__name__ if e.__cause__ else None
        print("%-8s VMError: %s (cause=%s)" % (name, e, cause))
    except SyntaxError as e:
        print("%-8s SyntaxError: %s" % (name, e))
    except IndexError as e:
        print("%-8s IndexError: %s" % (name, e))
    except AttributeError as e:
        print("%-8s AttributeError: %s" % (name, e))

code = Compiler(lex(PROGRAMS["prec"])).program()
print([(i.op.name, i.arg) for i in code[:6]])
print(Op.ADD, repr(Op.ADD), Op(4), int(Op["MUL"]), Kind.NUM, Kind.members["op"], len(Op))
print(Op.ADD + 1, isinstance(Op.ADD, int), Op.ADD == 4, hash(Op.ADD) == hash(4), {Op.ADD: "add"}[4])
print("%d|%s|%r" % (Op.LT, Op.LT, Op.LT), Op.LT * 2, -Op.LT, Op.LT // 2, Op.EQ > 3, 3 < Op.EQ)


def check(label, f):
    """Run one probe; print its result or the exception it raised."""
    try:
        print(label, f())
    except Exception as e:
        print(label, "raised", type(e).__name__, e)


# comparisons and arithmetic between two instances of an int subclass
check("lt", lambda: Op.PUSH < Op.LOAD)
check("eq", lambda: Op.PUSH == Opcode.by_value[1])
check("ne", lambda: Op.PUSH != Op.LOAD)
check("add", lambda: Op.PUSH + Op.LOAD)
check("sorted", lambda: sorted([Op.JZ, Op.PUSH, Op.EQ]))
check("max", lambda: max(Op).name)
check("list", lambda: list(Op)[:3])


# Constants that are instances of a __slots__ class stored as class attributes
# (a common "enum-like singleton" idiom).
class Reg:
    __slots__ = ("name", "num")

    def __init__(self, name, num):
        self.name = name
        self.num = num

    def __repr__(self):
        return "Reg(%s)" % self.name


Reg.SP = Reg("sp", 0)
Reg.PC = Reg("pc", 1)
check("slots-const", lambda: (Reg.SP, Reg.PC.num, getattr(Reg, "SP").name, vars(Reg)["PC"]))
