# Lexical and grammatical errors: compile() and exec() must raise a
# catchable SyntaxError (messages are not compared).

sources = [
    # unterminated / malformed string literals
    "x = 'abc",
    'x = "abc',
    "x = '''abc",
    'x = """abc\n\n',
    "x = 'abc\ndef'",
    "x = 'abc\\'",
    "x = r'\\'",
    # invalid characters
    "x = 1 $ 2",
    "x = a ? b : c",
    "x = `1`",
    "x = 1 \\ 2",
    # malformed numbers
    "x = 0777",
    "x = 09",
    "x = 1__0",
    "x = 1_",
    "x = 0x",
    "x = 0b2",
    "x = 0o8",
    "x = 1e",
    "x = 0x_",
    "x = 1._5",
    "x = 1_.5",
    "x = 0_7",
    # grammar errors
    "x = = 1",
    "1 +",
    "def f(:\n    pass",
    "if x\n    pass",
    "for in x: pass",
    "x = (1, 2",
    "x = [1, 2)",
    "x = {1: 2",
    "print 'hello'",
    "a b c",
    "x = 1 +* 2",
    "def f(a, a=1, b): pass",
    "class C(: pass",
    "lambda x: (yield)",
    "x = 1 if 2",
    "import",
    "from x import",
    "from . import (a, b",
    "x = yield = 1",
    "else: pass",
    "elif x: pass",
    "try:\n    pass\n",
    "while True\n    pass",
    "x.1 = 2",
    "None = 1",
    "True = 1",
    "def None(): pass",
    "x = not",
    "with: pass",
    ")",
    "]",
    "}",
    "x = ()()",
    # valid sources, for contrast
    "x = 'ok'",
    "x = 0",
    "x = 00",
    "x = 0_0",
    "x = 1_0",
    "x = 0e0",
    "x = 0j",
    "x = 1 if 2 else 3",
]
for src in sources:
    try:
        compile(src, '<test>', 'exec')
        result = 'compiled'
    except SyntaxError:
        result = 'SyntaxError'
    except Exception as e:
        result = 'wrong exception ' + type(e).__name__
    print(repr(src), result)

# the error is raised before any statement of the source runs
ran = []
try:
    exec("ran.append(1)\nx = (", {'ran': ran})
except SyntaxError:
    print('SyntaxError raised; ran =', ran)

# SyntaxError from eval()
for src in ['1 +', '', 'x = 1', 'if 1: pass', '(1, 2', 'lambda: ']:
    try:
        eval(src)
        print(repr(src), 'evaluated')
    except SyntaxError:
        print(repr(src), 'SyntaxError')
    except Exception as e:
        print(repr(src), 'wrong exception', type(e).__name__)
