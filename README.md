# boros

A metacircular Python interpreter written in Python. It tokenizes, parses and compiles Python 3.13 source code itself
(it never calls the host's `eval`, `exec` or `compile`, and does not use the `ast` module), and it is written in the
subset of Python it implements, so it can run itself, which can run itself, and so on. (Ouroboros: the snake eating its
own tail.)

```bash
uv run python -m boros program.py                     # L1: boros runs program.py
uv run python -m boros -m boros program.py            # L2: boros runs boros, which runs program.py
uv run python -m boros -m boros -m boros program.py   # L3
uv run python bench/tower.py 3 program.py             # the same as L3, for any level
```

`-c command` and `-m module` work like CPython's. Without uv, use `PYTHONPATH=src python -m boros ...`.

## The tower: boros running boros running boros ...

How long does a simple statement take when the interpreter runs itself, again and again? `bench/simple_statement.py`
times `x = x + 1` (unrolled ten times in a loop, minus an identical empty loop, best of five runs), at each level of the
tower. L0 is CPython 3.13; L*n* is CPython running boros running boros ... (*n* copies) running the benchmark.

![Time per statement at each level](bench/results/levels.png)

| Level | Time per statement | vs. level below | vs. CPython | Start-up |
|---|---:|---:|---:|---:|
| L0 (CPython) | 14.8 ns |  | ×1 | 17 ms |
| L1 | 98.2 ns | ×6.7 | ×7 | 106 ms |
| L2 | 935 ns | ×9.5 | ×63 | 504 ms |
| L3 | 12.2 µs | ×13.0 | ×824 | 4.5 s |
| L4 | 191 µs | ×15.7 | ×12,925 | 48.1 s |
| L5 | 2.14 ms | ×11.2 | ×144,786 | 10.1 min |
| L6 | 28.0 ms | ×13.1 | ×1,900,799 | 2.0 h |

The first level costs about ×7: boros runs the benchmark directly, compiling `x = x + 1` into a couple of
specialized closures. From level 2 on, what is being interpreted is mostly the interpreter itself, calling its own
closures and reading its own objects, so each further level multiplies the cost by roughly ×10 to ×16. The variation
between levels shows no clear trend: repeated runs on the same (shared) machine differ by up to about 15%, levels 4 to 6 were
run only once each, and turning off the host's garbage collector changes nothing. Start-up grows by a similar factor per level, because before running
anything each level parses and compiles the interpreter's own source while being interpreted itself; at level 6 that
takes two hours.

```bash
uv run python bench/run_levels.py 5    # measure L0..L5 into bench/results/levels.json (about 12 minutes)
uv run python bench/run_levels.py 6 --min-level 6    # add L6 (about 2 hours)
uv run python bench/plot_levels.py     # draw bench/results/levels.png
uv run python bench/make_page.py       # render bench/results/tower.html, an interactive version of the chart
```

## Tests

```bash
uv run pytest -n auto -m "not selfhost"   # every program in tests/cases/ under CPython vs boros
uv run pytest -n auto -m selfhost         # the same programs under boros running boros
```

The tests are differential: each program in `tests/cases/` is run by CPython and by boros, and their standard output,
exit status and final error line must match. `tests/test_no_host_eval.py` checks that the interpreter never references
the host's `eval`/`exec`/`compile`, never imports `ast`/`code`/`dis`/`marshal`, and still works in a process where those
host builtins have been deleted.

## Layout

```
src/boros/
  syntax.py             syntax tree node classes and Scope (name-binding facts)
  lexer.py              tokenizer and literal decoding
  core_types.py         type aliases shared by the whole package (Frame, ExprFn, ...)
  parser/               recursive-descent parser: statements, expressions, strings, patterns,
                        unparse (for `from __future__ import annotations`)
  compiler/             syntax tree -> closures: compiler (name resolution, dispatch), scopes,
                        names, operators, calls, expressions, comprehensions, targets,
                        statements, definitions, patterns, generators
  runtime/              the object model programs run on: objects, lookup, attributes, calls,
                        protocols, object_methods, classes, typechecks, errors, exceptions,
                        tracebacks, coroutines, builtin_functions, modules, suggestions,
                        introspection, host_overrides, type_alias
  cli.py, __main__.py   `python -m boros`
tests/                  differential test harness; tests/cases/ holds the test programs
bench/                  the interpreter-tower benchmark and its plot
```

## Development

```bash
uv run ruff check        # lint (default rules plus cyclomatic complexity <= 10 and annotations)
uv run pyright           # type check (standard mode)
uv run pytest -n auto    # all tests, including boros running boros
```

`tests/cases/` is excluded from ruff and pyright: those programs deliberately contain errors, which the tests compare
against CPython's behaviour.

## Explanation

### The big picture

Running a program goes through four stages, each in its own part of the package:

```
source text --lexer--> tokens --parser--> syntax tree --compiler--> tree of closures --run--> results
              lexer.py           parser/      syntax.py   compiler/                    runtime/
```

The interesting design decision is the third arrow. Instead of walking the syntax tree every time code runs (a
"tree-walking" interpreter), or translating it to bytecode for a virtual machine loop (what CPython does), boros
*compiles each syntax-tree node once into an ordinary Python closure*. An expression becomes a function
`f(fr) -> value`; a statement becomes a function `f(fr) -> signal`, where `fr` is the frame (a dict of local
variables). For example `x + 1`, where `x` is a local variable, compiles to roughly

```python
def add_local_const(fr):
    return fr['x'] + 1
```

and `y = x + 1` to a closure that calls that one and stores the result in `fr['y']`. Running a program is just calling
the closure for its module body with the module's globals dict. There is no dispatch on node types at run time: every
decision that can be made by looking at the code (which operator, which kind of variable, how many arguments) is made
once at compile time, by choosing which closure to build. This is why boros is only about 7x slower than CPython on
simple statements, and it matters even more when boros runs itself (see *Self-hosting* below).

### Lexing (`lexer.py`)

`tokenize()` turns source text into a list of `(kind, value, line)` tuples: `NAME`, `NUMBER`, `STRING`, `OP`,
`NEWLINE`, `INDENT`, `DEDENT` and `EOF`. A single regular expression recognizes the next token; the tokenizer tracks
bracket depth (newlines inside brackets do not end a statement) and a stack of indentation widths, emitting
`INDENT`/`DEDENT` tokens when the indentation of a logical line changes, exactly as Python's grammar specifies.

String literals are found with per-quote-style regular expressions; f-strings are scanned by hand
(`scan_fstring`) because their `{...}` replacement fields can contain nested strings and even nested f-strings.
Escape sequences (`\n`, `\x41`, `é`, `\N{BULLET}`, octal, line continuations) are decoded by the lexer's
helpers; numbers are converted with `int(text, 0)`, `float()` and `complex()`, which is the host doing arithmetic
conversion, not evaluation.

### Parsing (`parser/`, `syntax.py`)

The parser is a hand-written recursive-descent parser that produces the node classes in `syntax.py`
(`Name`, `BinOp`, `Call`, `If`, `FunctionDef`, ...). It is split into mixins combined into one `Parser` class:
`statements.py` (simple and compound statements, function and class definitions, parameter lists), `expressions.py`,
`strings.py` (adjacent literal concatenation and f-strings, whose expressions are parsed by a sub-parser) and
`patterns.py` (the `match` statement). Binary operators use *precedence climbing*: one function `binary(min_prec)`
handles all eleven precedence levels with a table, instead of one function per level, which keeps the recursion shallow.

While parsing, the parser also collects the facts needed for name resolution into a `Scope` object for every module,
function, lambda and class: which names are assigned (and therefore local), declared `global` or `nonlocal`, deleted,
whether the function contains `yield` (so it is a generator) or uses `super()`/`__class__`. It also performs
private-name mangling (`__x` inside `class C` becomes `_C__x`).

### Name resolution (`compiler/scopes.py`, `compiler/compiler.py`)

Python decides at compile time whether each name is local, global or a free variable from an enclosing function, and
so does boros. The `Compiler` keeps a stack of scopes; `Compiler.resolve(name)` answers:

* **local**: assigned in the current function. Loads compile to `fr[name]`.
* **global**: loads look in the module's globals dict and then the builtins dict. The globals dict is known at compile
  time, so the closure captures it directly.
* **free** with a depth: bound in an enclosing function. Every frame of a function that has a closure contains the
  key `'.up'`, pointing to the frame of the function it was defined in, so a free variable at depth 2 is
  `fr['.up']['.up'][name]`. This "environment chain" gives exactly Python's closure semantics (late binding, `nonlocal`
  rebinding) because each call creates a fresh frame dict that inner functions keep alive.
* **class namespace**: inside a class body, names are looked up in the class namespace first, then globally, and the
  functions defined in a class body skip the class scope, as in Python.

Keys starting with `'.'` can never be identifiers, so the frame dict doubles as storage for interpreter bookkeeping:
`'.up'` (enclosing frame), `'.rv'` (return value), `'.cls'` (the class cell used by zero-argument `super()`), `'.tN'`
(temporaries of generator mode).

Comprehensions get their own scope (their loop variables do not leak), while walrus targets inside them bind in the
enclosing function, as in Python 3.

### Compiling (`compiler/`)

`Compiler.expr(node)` and `Compiler.stmt(node)` look up the compile function for the node's type in a table
(`compile_binop`, `compile_if`, ...), and each compile function returns a closure. The compiler is organized by
topic: `names.py` (variable loads/stores), `operators.py`, `calls.py`, `expressions.py` (attributes, subscripts,
displays, f-strings), `comprehensions.py`, `targets.py` (assignment targets and unpacking), `statements.py`,
`definitions.py` (`def`, `class`, `lambda`), `patterns.py` (`match`) and `generators.py`.

**Control flow.** A statement closure returns `None` to continue, or one of three signal objects: `BREAK`,
`CONTINUE` or `RETURN` (the return value is stored in `fr['.rv']`). A block runs its statement closures in order and
passes any signal up; a loop consumes `BREAK` and `CONTINUE`; a function body turns `RETURN` into the call's result.
Exceptions are host exceptions: `raise` raises one, and `try`/`except`/`finally` are implemented with a host
`try`/`except`/`finally` around the body closure, so exception propagation, `finally` and `return` inside `finally`
behave exactly as in Python.

**Specialization.** Compile functions choose among several closure variants for the common shapes of code: an
operator whose left operand is a local variable and right operand a constant (`i + 1`, `n < 10`), a call whose callee is
a free variable and whose single argument is a parameter (`body(fr)`, the shape of almost every call between the
interpreter's own closures), a subscript `fr[name]`, and so on. Function parameters are always bound (unless deleted),
so loading them needs no "unbound local variable" check. Each specialization removes a closure call, and when boros
runs itself every closure call it saves at one level saves a whole interpreted function call at the level below.

**Tracebacks.** Block closures wrap their statements in a host `try` (free in CPython 3.11+ until an exception
happens); when an exception passes through, they record the frame and line number on the host exception object, so an
uncaught error prints a real Python-style traceback with interpreted file names, line numbers and source lines.

### Functions and calls (`runtime/objects.py`, `runtime/calls.py`)

`def` creates a `Function` holding a `Code` object (parameter names, flags, the compiled body), its default values,
its globals and its closure (the defining frame). `invoke(f, args, kwargs)` creates the frame: in the common case of
exactly the right number of positional arguments it is just `dict(zip(params, args))` plus the `'.up'` link;
otherwise `bind_args()` implements Python's full argument binding (defaults, `*args`, `**kwargs`, keyword-only and
positional-only parameters) with CPython's error messages. The call closures in `compiler/calls.py` inline that fast
path for one- and two-argument calls.

`call(f, args, kwargs)` calls anything: interpreted functions, bound methods, interpreted classes (instantiation),
instances with `__call__`, and host callables (builtins, host methods, host classes).

### Classes and instances (`runtime/objects.py`, `lookup.py`, `attributes.py`, `classes.py`)

Interpreted classes are `Class` objects, not host classes. A `Class` has a namespace dict and a method resolution
order computed with the C3 algorithm; the MRO may include host types (`object`, `Exception`, `list`, ...). Instances
are `Instance` objects with an attribute dict (`d`), slot storage for classes with `__slots__` (`sv`), and, for classes
deriving from a host type, a `native` host object that stands in for the base-class part, for example the real
exception object behind an interpreted `class MyError(ValueError)`.

Attribute lookup follows Python's descriptor protocol exactly. `lookup(cls, name)` walks the MRO and caches, per
class, an entry `(kind, value, owner)` that *classifies* the attribute: plain value, function (binds to a method),
`staticmethod`, `classmethod`, `property`, slot, interpreted or host data/non-data descriptor, an attribute of a host
base class, or one of the emulated methods of `object`. `inst_getattr` then needs only a dictionary lookup and a
comparison in the common cases (instance attribute, method). Assigning to a class attribute clears the caches of the
class and its subclasses. `__getattr__`, `__getattribute__`, `__setattr__` and `__delattr__` overrides,
`super()` (zero-argument, via the class cell, and two-argument), `__init_subclass__`, `__set_name__`, `__class__`
assignment and name mangling are all implemented.

A class whose metaclass is a host metaclass, such as `enum.EnumType` or `typing.NamedTupleMeta`, is made by that
metaclass: it is a host class holding interpreted functions, which the host binds as methods because `Function` defines
`__get__`. `abc.ABCMeta` is emulated instead, so abstract base classes stay interpreted classes (with
`__abstractmethods__`, `register()` and the check that refuses to instantiate an abstract class).

### Special methods (`runtime/protocols.py`, `runtime/object_methods.py`)

Interpreted values mix freely with host values: an interpreted list is a host list, and `print`, `sorted` or `+` are
the host's. To make host operations work on interpreted objects, the host `Instance` class defines every special
method (`__add__`, `__radd__`, `__iadd__`, `__eq__`, `__lt__`, `__hash__`, `__len__`, `__iter__`, `__next__`,
`__getitem__`, `__call__`, `__repr__`, `__format__`, `__enter__`, ...) and forwards it to the interpreted class with
`call_special()`. So `a + b` in an interpreted program runs the host's `+`, which calls `Instance.__add__`, which runs
the interpreted `__add__` method, and `sorted(objects)` works because the host's comparisons reach the interpreted
`__lt__`. The forwarding methods implement Python's full binary-operator protocol (reflected operands, the subclass
priority rule, `NotImplemented`) and produce CPython's error messages with the interpreted class names.

When a lookup reaches the host `object` type at the end of an MRO, boros uses its own emulations of `object`'s
methods (`object_methods.py`): default `__init__`, `__repr__` (`<__main__.C object at 0x...>`), identity
`__eq__`/`__hash__`, `__format__`, `__setattr__`, and so on.

### Generators (`compiler/generators.py`)

A function containing `yield` is compiled in *generator mode*: every statement that contains a `yield` compiles to a
host generator function instead of a plain closure, and a `yield` expression compiles to a host `yield`. Compound
statements delegate to their children with `yield from`, so when the interpreted generator is suspended, the whole
chain of closures executing it is suspended with it. Calling an interpreted generator function therefore returns a
genuine host generator object, and `next`, `send`, `throw`, `close`, `yield from` delegation and `return` values all
behave as in Python. An expression with a `yield` in the middle (`f(a, (yield b), c)`) is rewritten so that its
sub-expressions are evaluated, in order, into frame temporaries first. `async def` functions are compiled the same
way, with `await` acting like `yield from`; calling one returns a real host coroutine (made by an `async def` inside
boros, `runtime/coroutines.py`), so asyncio accepts it at every level of the tower, and an `async def` containing
`yield` returns an async generator object.

Two host rules need care. A `StopIteration` leaving any host generator frame becomes `RuntimeError` (PEP 479), so
interpreted code inside the chain raises it wrapped in a private carrier exception, which `except` clauses see as the
`StopIteration`; only the outermost frame turns an uncaught one into `RuntimeError`. And `close()` on a generator
suspended in `yield from` closes the chain from the innermost generator outwards, raising `GeneratorExit` again in
every frame, so an interpreted `except GeneratorExit:` could not continue. A generator whose `try` or `with`
statements could stop that `GeneratorExit` therefore runs under `drive()`, an outer host generator that forwards
values with a plain `yield` and delivers `close()` into the chain as an ordinary exception, which the innermost
interpreted yield turns back into `GeneratorExit`.

### Exceptions (`runtime/errors.py`, `runtime/exceptions.py`)

Exceptions are always host exception objects, so host code (a `for` loop seeing `StopIteration`, a host library
catching `KeyError`) interacts with interpreted code correctly. An instance of an interpreted exception class is raised
as its `native` part, which carries a back-reference to the `Instance`; `except` clauses map it back with
`exc_value()` and match against interpreted or host classes. The attribute names used for back-references and
tracebacks include a per-interpreter id, so that nested copies of boros, which share the same host exception objects,
do not see each other's bookkeeping. Implicit and explicit exception chaining (`__context__`, `raise ... from`) is the
host's, and the top level prints chained tracebacks like CPython.

Where host objects hand out exceptions, interpreted code must get the interpreted ones back: reads of `__cause__`,
`__context__`, `exceptions`, `sys.exc_info` and `sys.exception` are compiled to `getattr_special`, a `with` statement
passes host context managers the host exception object, and `import traceback` gives a copy of the host module whose
formatting functions use the interpreter's own (`runtime/tracebacks.py`). `except*` splits an exception group by the
clause types with the host's `split()`, and combines what the clauses raise as CPython does.

### Builtins and modules (`runtime/builtin_functions.py`, `runtime/modules.py`)

Interpreted programs see the host builtins, except for those that must understand interpreted objects or the current
frame: `isinstance`, `issubclass`, `type`, `super`, `callable`, `getattr`/`setattr`/`hasattr`/`delattr`, `vars`, `dir`,
`locals`, `globals`, `__import__`, and `eval`/`exec`/`compile`, which boros implements with its own lexer, parser and
compiler. Calls to `locals()`, `super()` and friends are recognized at compile time so that they receive the caller's
frame.

`import` interprets `.py` modules and packages found next to the main script (and the boros package itself);
anything else (`sys`, `re`, `time`, `json`, ...) is imported from the host, the way CPython's C extension modules are
"native". Relative imports, packages, `from m import *`, `__all__` and circular imports work. A few host library
functions cannot work on interpreted classes: `dataclasses` is therefore interpreted from the standard library's source,
and programs get a `functools` whose `total_ordering` understands interpreted classes.

### Self-hosting

Because boros is written in the Python it implements, it can interpret its own source: at level 2, the host runs boros
(L1), L1 compiles boros's source into closures and runs it (that is L2), and L2 compiles and runs the program. Each
level shares the host's values (ints, lists, dicts, native modules), but has its own module table, classes, frames
and traceback bookkeeping. `cli.py` runs every level in a thread with a large stack and a high recursion limit,
because each interpreted call costs several host frames, multiplied at every level.

The cost of one more level is dominated by what the interpreter itself does per operation when it is interpreted:
mostly calling its own closures (`invoke`) and reading attributes of its own objects. That is why the compile-time
specializations and the inlined call fast paths matter so much: they reduce the number of interpreted calls per
operation, and the saving compounds at every level of the tower.

## Limitations

The cases boros does not pass yet are listed, with reasons, in `tests/known_failures.py` (they run as strict expected
failures). In short:

* Interpreted classes are not host types. Host C code that checks exact types therefore rejects them or their
  instances: `str.join` or `json.dumps` given instances of interpreted `str`/`dict` subclasses,
  `unittest.assertRaises` and `functools.singledispatch.register` given interpreted classes, exception objects that
  asyncio hands back. Some error messages produced by CPython itself also name the host type `Instance`, or the
  reflected form of a comparison, instead of the interpreted class.
* Host code reading attributes of interpreted objects with `operator.attrgetter` or `str.format` sees the interpreter's
  own `Instance` fields (`cls`, `d`, `native`, `sv`) under those names.
* Metaclasses written in Python are not supported (host metaclasses such as `enum.EnumType` are); `__del__` is never
  called for interpreted objects.
* When boros runs itself, host code that sets attributes on the inner interpreter's objects (`functools.wraps` on an
  inner function, for example) bypasses the interpreted properties that hold them, and an interpreted `type()` cannot
  create the host shadow classes that subclasses of pure-Python host classes need.
