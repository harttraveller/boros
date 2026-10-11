"""A tiny Scheme interpreter: tokenizer, reader producing nested lists,
environments chained through a class, special forms, closures, tail-call
elimination with a trampoline loop, a few builtins, and error reporting."""
import math
import operator as op


class Symbol(str):
    pass


class LispError(Exception):
    pass


def tokenize(src):
    return src.replace("(", " ( ").replace(")", " ) ").replace("'", " ' ").split()


def read(tokens):
    if not tokens:
        raise LispError("unexpected EOF")
    tok = tokens.pop(0)
    if tok == "(":
        lst = []
        while tokens and tokens[0] != ")":
            lst.append(read(tokens))
        if not tokens:
            raise LispError("missing )")
        tokens.pop(0)
        return lst
    if tok == ")":
        raise LispError("unexpected )")
    if tok == "'":
        return [Symbol("quote"), read(tokens)]
    for conv in (int, float):
        try:
            return conv(tok)
        except ValueError:
            pass
    if tok == "#t":
        return True
    if tok == "#f":
        return False
    return Symbol(tok)


def parse_all(src):
    tokens = tokenize(src)
    out = []
    while tokens:
        out.append(read(tokens))
    return out


class Env(dict):
    def __init__(self, params=(), args=(), outer=None):
        super().__init__()
        if len(params) != len(args):
            raise LispError("expected %d args, got %d" % (len(params), len(args)))
        self.update(zip(params, args))
        self.outer = outer

    def find(self, name):
        e = self
        while e is not None:
            if name in e:
                return e
            e = e.outer
        raise LispError("unbound symbol: %s" % name)


class Lambda:
    def __init__(self, params, body, env, name="lambda"):
        self.params, self.body, self.env, self.name = params, body, env, name

    def __repr__(self):
        return "#<procedure %s>" % self.name


def standard_env():
    env = Env()
    env.update({
        "+": lambda *a: sum(a), "-": lambda a, b=None: -a if b is None else a - b,
        "*": lambda *a: math.prod(a), "/": op.truediv, "<": op.lt, ">": op.gt, "=": op.eq,
        "<=": op.le, "abs": abs, "car": lambda x: x[0], "cdr": lambda x: x[1:],
        "cons": lambda x, y: [x] + y, "list": lambda *x: list(x), "null?": lambda x: x == [],
        "length": len, "apply": lambda f, args: apply(f, args), "map": lambda f, xs: [apply(f, [x]) for x in xs],
        "modulo": op.mod, "not": op.not_, "max": max, "min": min, "even?": lambda n: n % 2 == 0,
        "display": lambda x: OUTPUT.append(to_str(x)),
    })
    return env


OUTPUT = []


def apply(f, args):
    if isinstance(f, Lambda):
        return evaluate(f.body, Env(f.params, args, f.env))
    if callable(f):
        return f(*args)
    raise LispError("not a procedure: %s" % to_str(f))


def evaluate(x, env):
    while True:
        if isinstance(x, Symbol):
            return env.find(x)[x]
        if not isinstance(x, list):
            return x
        if not x:
            raise LispError("empty application")
        head = x[0]
        if head == "quote":
            return x[1]
        if head == "if":
            _, test, conseq, alt = x
            x = conseq if evaluate(test, env) is not False else alt
            continue
        if head == "define":
            if isinstance(x[1], list):
                name, *params = x[1]
                env[name] = Lambda(params, x[2], env, name)
            else:
                env[x[1]] = evaluate(x[2], env)
            return None
        if head == "set!":
            env.find(x[1])[x[1]] = evaluate(x[2], env)
            return None
        if head == "lambda":
            return Lambda(x[1], x[2], env)
        if head == "begin":
            for e in x[1:-1]:
                evaluate(e, env)
            x = x[-1]
            continue
        if head == "let":
            names = [b[0] for b in x[1]]
            vals = [evaluate(b[1], env) for b in x[1]]
            env = Env(names, vals, env)
            x = x[2]
            continue
        if head == "cond":
            for clause in x[1:]:
                if clause[0] == "else" or evaluate(clause[0], env) is not False:
                    x = clause[1]
                    break
            else:
                return None
            continue
        f = evaluate(head, env)
        args = [evaluate(a, env) for a in x[1:]]
        if isinstance(f, Lambda):
            env = Env(f.params, args, f.env)
            x = f.body
            continue
        try:
            return apply(f, args)
        except (TypeError, ZeroDivisionError, IndexError) as e:
            raise LispError("error in (%s ...): %s" % (to_str(head), type(e).__name__)) from e


def to_str(x):
    if x is True:
        return "#t"
    if x is False:
        return "#f"
    if isinstance(x, list):
        return "(" + " ".join(map(to_str, x)) + ")"
    if isinstance(x, float) and x.is_integer():
        return str(int(x)) + ".0"
    return str(x)


PROGRAM = """
(define (fact n) (if (<= n 1) 1 (* n (fact (- n 1)))))
(fact 20)
(define (count-to n acc) (if (= n 0) acc (count-to (- n 1) (+ acc 1))))
(count-to 3000 0)
(define (fib n) (cond ((< n 2) n) (else (+ (fib (- n 1)) (fib (- n 2))))))
(map fib '(0 1 2 3 4 5 6 7 8 9 10))
(define make-counter (lambda () (let ((n 0)) (lambda () (begin (set! n (+ n 1)) n)))))
(define c1 (make-counter))
(define c2 (make-counter))
(begin (c1) (c1) (c2) (list (c1) (c2)))
(define (filter p xs) (cond ((null? xs) '()) ((p (car xs)) (cons (car xs) (filter p (cdr xs)))) (else (filter p (cdr xs)))))
(filter even? '(1 2 3 4 5 6 7 8))
(define (compose f g) (lambda (x) (f (g x))))
((compose abs -) 7)
(apply max '(3 9 2))
(let ((x 2) (y 3)) (* x y 1.5))
(display (list 'done #t #f 2.0))
fact
"""

env = standard_env()
for expr in parse_all(PROGRAM):
    result = evaluate(expr, env)
    if result is not None:
        print(to_str(result))
print(OUTPUT)
ERRORS = ["(car '())", "(undefined-fn 1)", "(/ 1 0)", "((lambda (x) x))", "(1 2)", "(+ 1", ")", "()", "(fact 'a)"]
for src in ERRORS:
    try:
        print(to_str(evaluate(parse_all(src)[0], env)))
    except LispError as e:
        cause = e.__cause__
        print("%-20s LispError: %s%s" % (src, e, " <- " + type(cause).__name__ if cause else ""))
print(isinstance(Symbol("x"), str), Symbol("ab") + "c", repr(Symbol("q")), env.find("fact") is env, len(env) > 20)
