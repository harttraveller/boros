"""The syntax tree produced by the parser and consumed by the compiler.

Every node records the source line it came from.  `_fields` lists the
attributes holding children, in evaluation order, so that generic passes
(such as the generator-mode compiler) can walk and rebuild nodes.
"""

from __future__ import annotations

from typing import Any


class Node:
    """Base class of all syntax tree nodes."""

    _fields: tuple[str, ...] = ()
    line: int

    def __init__(self, line: int) -> None:
        self.line = line

    def __repr__(self) -> str:
        parts: list[str] = [f'{f}={getattr(self, f, None)!r}' for f in self._fields]
        return f"{type(self).__name__}({', '.join(parts)})"


class Expression(Node):
    """A node that evaluates to a value."""


class Statement(Node):
    """A node that is executed for its effect."""


class Pattern(Node):
    """A pattern of a `match` statement case."""


# -- expressions ---------------------------------------------------------------

class Name(Expression):
    _fields = ('id',)

    def __init__(self, line: int, id: str) -> None:
        self.line = line
        self.id = id


class Const(Expression):
    _fields = ('value',)

    def __init__(self, line: int, value: Any) -> None:
        self.line = line
        self.value = value


class JoinedStr(Expression):
    """An f-string: literal parts (Const) and FormattedValue parts."""
    _fields = ('values',)

    def __init__(self, line: int, values: list[Expression]) -> None:
        self.line = line
        self.values = values


class FormattedValue(Expression):
    """A `{value!conv:spec}` replacement field of an f-string."""
    _fields = ('value', 'conv', 'spec')

    def __init__(self, line: int, value: Expression, conv: str | None, spec: JoinedStr | None) -> None:
        self.line = line
        self.value = value
        self.conv = conv
        self.spec = spec


class Tuple(Expression):
    _fields = ('elts',)

    def __init__(self, line: int, elts: list[Expression]) -> None:
        self.line = line
        self.elts = elts


class List(Expression):
    _fields = ('elts',)

    def __init__(self, line: int, elts: list[Expression]) -> None:
        self.line = line
        self.elts = elts


class SetDisplay(Expression):
    _fields = ('elts',)

    def __init__(self, line: int, elts: list[Expression]) -> None:
        self.line = line
        self.elts = elts


class DictDisplay(Expression):
    """A dict display; a key of None marks a `**mapping` entry."""
    _fields = ('keys', 'values')

    def __init__(self, line: int, keys: list[Expression | None], values: list[Expression]) -> None:
        self.line = line
        self.keys = keys
        self.values = values


class Starred(Expression):
    _fields = ('value',)

    def __init__(self, line: int, value: Expression) -> None:
        self.line = line
        self.value = value


class BinOp(Expression):
    _fields = ('left', 'op', 'right')

    def __init__(self, line: int, left: Expression, op: str, right: Expression) -> None:
        self.line = line
        self.left = left
        self.op = op
        self.right = right


class UnaryOp(Expression):
    _fields = ('op', 'operand')

    def __init__(self, line: int, op: str, operand: Expression) -> None:
        self.line = line
        self.op = op
        self.operand = operand


class BoolOp(Expression):
    _fields = ('op', 'values')

    def __init__(self, line: int, op: str, values: list[Expression]) -> None:
        self.line = line
        self.op = op
        self.values = values


class Compare(Expression):
    _fields = ('left', 'ops', 'comparators')

    def __init__(self, line: int, left: Expression, ops: list[str], comparators: list[Expression]) -> None:
        self.line = line
        self.left = left
        self.ops = ops
        self.comparators = comparators


class Keyword(Node):
    """A keyword argument `arg=value`; arg is None for `**value`."""
    _fields = ('arg', 'value')

    def __init__(self, line: int, arg: str | None, value: Expression) -> None:
        self.line = line
        self.arg = arg
        self.value = value


class Call(Expression):
    _fields = ('func', 'args', 'keywords')

    def __init__(self, line: int, func: Expression, args: list[Expression], keywords: list[Keyword]) -> None:
        self.line = line
        self.func = func
        self.args = args
        self.keywords = keywords


class Attribute(Expression):
    _fields = ('value', 'attr')

    def __init__(self, line: int, value: Expression, attr: str) -> None:
        self.line = line
        self.value = value
        self.attr = attr


class Subscript(Expression):
    _fields = ('value', 'index')

    def __init__(self, line: int, value: Expression, index: Expression) -> None:
        self.line = line
        self.value = value
        self.index = index


class Slice(Expression):
    _fields = ('lower', 'upper', 'step')

    def __init__(self, line: int, lower: Expression | None, upper: Expression | None,
                 step: Expression | None) -> None:
        self.line = line
        self.lower = lower
        self.upper = upper
        self.step = step


class IfExp(Expression):
    _fields = ('test', 'body', 'orelse')

    def __init__(self, line: int, test: Expression, body: Expression, orelse: Expression) -> None:
        self.line = line
        self.test = test
        self.body = body
        self.orelse = orelse


class Arguments(Node):
    """The parameter list of a function or lambda.  `defaults` belong to the
    last positional parameters; `kw_defaults` parallels `kwonly`.
    `annotations` lists (parameter name, annotation) in signature order,
    then ('return', annotation) for a return annotation."""
    _fields = ('posonly', 'args', 'defaults', 'vararg', 'kwonly', 'kw_defaults', 'kwarg', 'annotations')

    def __init__(self, line: int, posonly: list[str], args: list[str], defaults: list[Expression],
                 vararg: str | None, kwonly: list[str], kw_defaults: list[Expression | None],
                 kwarg: str | None, annotations: list[tuple[str, Expression]]) -> None:
        self.line = line
        self.posonly = posonly
        self.args = args
        self.defaults = defaults
        self.vararg = vararg
        self.kwonly = kwonly
        self.kw_defaults = kw_defaults
        self.kwarg = kwarg
        self.annotations = annotations


class Lambda(Expression):
    _fields = ('args', 'body', 'scope')

    def __init__(self, line: int, args: Arguments, body: Expression, scope: Scope) -> None:
        self.line = line
        self.args = args
        self.body = body
        self.scope = scope


class NamedExpr(Expression):
    """An assignment expression `target := value`."""
    _fields = ('target', 'value')

    def __init__(self, line: int, target: Name, value: Expression) -> None:
        self.line = line
        self.target = target
        self.value = value


class Comprehension(Node):
    """One `for target in iter if cond...` clause of a comprehension
    (`async for ...` if is_async)."""
    _fields = ('target', 'iter', 'ifs', 'is_async')

    def __init__(self, line: int, target: Expression, iter: Expression, ifs: list[Expression],
                 is_async: bool = False) -> None:
        self.line = line
        self.target = target
        self.iter = iter
        self.ifs = ifs
        self.is_async = is_async


class ListComp(Expression):
    _fields = ('elt', 'gens')

    def __init__(self, line: int, elt: Expression, gens: list[Comprehension]) -> None:
        self.line = line
        self.elt = elt
        self.gens = gens


class SetComp(Expression):
    _fields = ('elt', 'gens')

    def __init__(self, line: int, elt: Expression, gens: list[Comprehension]) -> None:
        self.line = line
        self.elt = elt
        self.gens = gens


class DictComp(Expression):
    _fields = ('key', 'value', 'gens')

    def __init__(self, line: int, key: Expression, value: Expression, gens: list[Comprehension]) -> None:
        self.line = line
        self.key = key
        self.value = value
        self.gens = gens


class GeneratorExp(Expression):
    _fields = ('elt', 'gens')

    def __init__(self, line: int, elt: Expression, gens: list[Comprehension]) -> None:
        self.line = line
        self.elt = elt
        self.gens = gens


class Yield(Expression):
    _fields = ('value',)

    def __init__(self, line: int, value: Expression | None) -> None:
        self.line = line
        self.value = value


class YieldFrom(Expression):
    _fields = ('value',)

    def __init__(self, line: int, value: Expression) -> None:
        self.line = line
        self.value = value


class Await(Expression):
    _fields = ('value',)

    def __init__(self, line: int, value: Expression) -> None:
        self.line = line
        self.value = value


class TypeAlias(Expression):
    """The value bound by `type name[params] = value`: a type alias whose
    value is computed when first needed, by calling `compute` (a lambda of
    the type parameters).  params are (kind, name) pairs, where kind is ''
    for a TypeVar, '*' for a TypeVarTuple and '**' for a ParamSpec."""
    _fields = ('name', 'params', 'compute')

    def __init__(self, line: int, name: str, params: list[tuple[str, str]], compute: Lambda) -> None:
        self.line = line
        self.name = name
        self.params = params
        self.compute = compute


class Temp(Expression):
    """A temporary slot in the frame, introduced by the generator-mode
    compiler when it evaluates sub-expressions that contain `yield`."""
    _fields = ('key',)

    def __init__(self, line: int, key: str) -> None:
        self.line = line
        self.key = key


# -- statements ----------------------------------------------------------------

class ExprStmt(Statement):
    """An expression evaluated for its side effects."""
    _fields = ('value',)

    def __init__(self, line: int, value: Expression) -> None:
        self.line = line
        self.value = value


class Assign(Statement):
    _fields = ('targets', 'value')

    def __init__(self, line: int, targets: list[Expression], value: Expression) -> None:
        self.line = line
        self.targets = targets
        self.value = value


class AugAssign(Statement):
    _fields = ('target', 'op', 'value')

    def __init__(self, line: int, target: Expression, op: str, value: Expression) -> None:
        self.line = line
        self.target = target
        self.op = op
        self.value = value


class AnnAssign(Statement):
    """`target: annotation = value` (value None without `= value`); simple
    is true when the target is a name that is not in parentheses."""
    _fields = ('target', 'annotation', 'value', 'simple')

    def __init__(self, line: int, target: Expression, annotation: Expression, value: Expression | None,
                 simple: bool) -> None:
        self.line = line
        self.target = target
        self.annotation = annotation
        self.value = value
        self.simple = simple


class Delete(Statement):
    _fields = ('targets',)

    def __init__(self, line: int, targets: list[Expression]) -> None:
        self.line = line
        self.targets = targets


class Pass(Statement):
    pass


class Break(Statement):
    pass


class Continue(Statement):
    pass


class Return(Statement):
    _fields = ('value',)

    def __init__(self, line: int, value: Expression | None) -> None:
        self.line = line
        self.value = value


class Raise(Statement):
    _fields = ('exc', 'cause')

    def __init__(self, line: int, exc: Expression | None, cause: Expression | None) -> None:
        self.line = line
        self.exc = exc
        self.cause = cause


class Global(Statement):
    _fields = ('names',)

    def __init__(self, line: int, names: list[str]) -> None:
        self.line = line
        self.names = names


class Nonlocal(Statement):
    _fields = ('names',)

    def __init__(self, line: int, names: list[str]) -> None:
        self.line = line
        self.names = names


class Assert(Statement):
    _fields = ('test', 'msg')

    def __init__(self, line: int, test: Expression, msg: Expression | None) -> None:
        self.line = line
        self.test = test
        self.msg = msg


class Import(Statement):
    """`import a.b as c, d`: names is a list of (dotted name, alias)."""
    _fields = ('names',)

    def __init__(self, line: int, names: list[tuple[str, str | None]]) -> None:
        self.line = line
        self.names = names


class ImportFrom(Statement):
    """`from ..module import a as b`: level counts the leading dots."""
    _fields = ('module', 'names', 'level')

    def __init__(self, line: int, module: str | None, names: list[tuple[str, str | None]], level: int) -> None:
        self.line = line
        self.module = module
        self.names = names
        self.level = level


class If(Statement):
    _fields = ('test', 'body', 'orelse')

    def __init__(self, line: int, test: Expression, body: list[Statement], orelse: list[Statement]) -> None:
        self.line = line
        self.test = test
        self.body = body
        self.orelse = orelse


class While(Statement):
    _fields = ('test', 'body', 'orelse')

    def __init__(self, line: int, test: Expression, body: list[Statement], orelse: list[Statement]) -> None:
        self.line = line
        self.test = test
        self.body = body
        self.orelse = orelse


class For(Statement):
    _fields = ('target', 'iter', 'body', 'orelse', 'is_async')

    def __init__(self, line: int, target: Expression, iter: Expression, body: list[Statement],
                 orelse: list[Statement], is_async: bool) -> None:
        self.line = line
        self.target = target
        self.iter = iter
        self.body = body
        self.orelse = orelse
        self.is_async = is_async


class ExceptHandler(Node):
    _fields = ('type', 'name', 'body')

    def __init__(self, line: int, type: Expression | None, name: str | None, body: list[Statement]) -> None:
        self.line = line
        self.type = type
        self.name = name
        self.body = body


class Try(Statement):
    """A try statement; `star` is true when its handlers are `except*` clauses."""

    _fields = ('body', 'handlers', 'orelse', 'finalbody', 'star')

    def __init__(self, line: int, body: list[Statement], handlers: list[ExceptHandler],
                 orelse: list[Statement], finalbody: list[Statement], star: bool = False) -> None:
        self.line = line
        self.body = body
        self.handlers = handlers
        self.orelse = orelse
        self.finalbody = finalbody
        self.star = star


class WithItem(Node):
    _fields = ('expr', 'target')

    def __init__(self, line: int, expr: Expression, target: Expression | None) -> None:
        self.line = line
        self.expr = expr
        self.target = target


class With(Statement):
    _fields = ('items', 'body', 'is_async')

    def __init__(self, line: int, items: list[WithItem], body: list[Statement], is_async: bool) -> None:
        self.line = line
        self.items = items
        self.body = body
        self.is_async = is_async


class FunctionDef(Statement):
    _fields = ('name', 'args', 'body', 'decorators', 'scope', 'is_async')

    def __init__(self, line: int, name: str, args: Arguments, body: list[Statement],
                 decorators: list[Expression], scope: Scope, is_async: bool) -> None:
        self.line = line
        self.name = name
        self.args = args
        self.body = body
        self.decorators = decorators
        self.scope = scope
        self.is_async = is_async


class ClassDef(Statement):
    _fields = ('name', 'bases', 'keywords', 'body', 'decorators', 'scope')

    def __init__(self, line: int, name: str, bases: list[Expression], keywords: list[Keyword],
                 body: list[Statement], decorators: list[Expression], scope: Scope) -> None:
        self.line = line
        self.name = name
        self.bases = bases
        self.keywords = keywords
        self.body = body
        self.decorators = decorators
        self.scope = scope


class MatchCase(Node):
    _fields = ('pattern', 'guard', 'body')

    def __init__(self, line: int, pattern: Pattern, guard: Expression | None, body: list[Statement]) -> None:
        self.line = line
        self.pattern = pattern
        self.guard = guard
        self.body = body


class Match(Statement):
    _fields = ('subject', 'cases')

    def __init__(self, line: int, subject: Expression, cases: list[MatchCase]) -> None:
        self.line = line
        self.subject = subject
        self.cases = cases


class Module(Node):
    _fields = ('body', 'scope')

    def __init__(self, line: int, body: list[Statement], scope: Scope) -> None:
        self.line = line
        self.body = body
        self.scope = scope


# -- match-statement patterns --------------------------------------------------

class PValue(Pattern):
    """A literal or dotted-name value, compared with ==."""
    _fields = ('value',)

    def __init__(self, line: int, value: Expression) -> None:
        self.line = line
        self.value = value


class PSingleton(Pattern):
    """None, True or False, compared with `is`."""
    _fields = ('value',)

    def __init__(self, line: int, value: bool | None) -> None:
        self.line = line
        self.value = value


class PCapture(Pattern):
    _fields = ('name',)

    def __init__(self, line: int, name: str) -> None:
        self.line = line
        self.name = name


class PWildcard(Pattern):
    pass


class PSequence(Pattern):
    _fields = ('patterns',)

    def __init__(self, line: int, patterns: list[Pattern]) -> None:
        self.line = line
        self.patterns = patterns


class PStar(Pattern):
    """`*name` inside a sequence pattern (name is None for `*_`)."""
    _fields = ('name',)

    def __init__(self, line: int, name: str | None) -> None:
        self.line = line
        self.name = name


class PMapping(Pattern):
    _fields = ('keys', 'patterns', 'rest')

    def __init__(self, line: int, keys: list[Expression], patterns: list[Pattern], rest: str | None) -> None:
        self.line = line
        self.keys = keys
        self.patterns = patterns
        self.rest = rest


class PClass(Pattern):
    _fields = ('cls', 'patterns', 'kwd_names', 'kwd_patterns')

    def __init__(self, line: int, cls: Expression, patterns: list[Pattern], kwd_names: list[str],
                 kwd_patterns: list[Pattern]) -> None:
        self.line = line
        self.cls = cls
        self.patterns = patterns
        self.kwd_names = kwd_names
        self.kwd_patterns = kwd_patterns


class POr(Pattern):
    _fields = ('patterns',)

    def __init__(self, line: int, patterns: list[Pattern]) -> None:
        self.line = line
        self.patterns = patterns


class PAs(Pattern):
    _fields = ('pattern', 'name')

    def __init__(self, line: int, pattern: Pattern, name: str) -> None:
        self.line = line
        self.pattern = pattern
        self.name = name


# -- scopes ----------------------------------------------------------------------

class Scope:
    """Name-binding facts about one function, lambda, class or module,
    collected by the parser and used by the compiler to resolve names.

    kind is 'module', 'function' or 'class' ('comp' scopes for
    comprehensions are created by the compiler)."""

    kind: str
    name: str
    parent: Scope | None
    assigned: set[str]
    globals: set[str]
    nonlocals: set[str]
    deleted: set[str]
    params: set[str]
    imported: set[str]
    loads: list[str]
    unloads: list[str]
    decl_lines: dict[str, int]
    argnames: list[str]
    vararg: str | None
    is_gen: bool
    has_yield: bool
    is_async: bool
    uses_class: bool
    qualname: str
    classname: str | None
    # Filled in by the compiler:
    # free variables the scope's code uses, or passes on to nested scopes:
    # name -> number of '.up' links from its frame to the frame holding it
    freevars: dict[str, int]
    # a class body that calls locals(), vars(), dir(), exec() or eval()
    uses_locals: bool
    # a list/set/dict comprehension inlined into the code around it (PEP 709)
    inlined: bool
    # the top level of exec()/eval() code with a separate locals mapping,
    # and whether that mapping is something other than a dict
    exec_locals: bool
    mapping: bool

    def __init__(self, kind: str, name: str, parent: Scope | None) -> None:
        self.kind = kind
        self.name = name
        self.parent = parent
        self.assigned = set()
        self.globals = set()
        self.nonlocals = set()
        self.deleted = set()
        self.params = set()
        # for the parser's checks of global and nonlocal declarations: the
        # names bound by imports, the names parsed as atoms so far and those
        # of them that turned out not to be loads (so a name has been loaded
        # if it occurs more often in `loads` than in `unloads`), and the line
        # of each name's first declaration
        self.imported = set()
        self.loads = []
        self.unloads = []
        self.decl_lines = {}
        self.argnames = []
        self.vararg = None
        self.is_gen = False
        self.has_yield = False
        self.is_async = False
        self.uses_class = False
        self.freevars = {}
        self.qualname = scope_qualname(kind, name, parent)
        # nearest enclosing class name, for private-name mangling
        if parent is None:
            self.classname = None
        elif parent.kind == 'class':
            self.classname = parent.name
        else:
            self.classname = parent.classname
        self.freevars = {}
        self.uses_locals = False
        self.inlined = False
        self.exec_locals = False
        self.mapping = False


def scope_qualname(kind: str, name: str, parent: Scope | None) -> str:
    """The __qualname__ of a function or class defined in `parent`."""
    if parent is None or parent.kind == 'module':
        return name
    if parent.kind == 'class':
        return parent.qualname + '.' + name
    return parent.qualname + '.<locals>.' + name


def collect_target_names(t: Node, out: set[str]) -> None:
    """Add the names bound by assignment target t to out."""
    if isinstance(t, Name):
        out.add(t.id)
    elif isinstance(t, (Tuple, List)):
        for e in t.elts:
            collect_target_names(e, out)
    elif isinstance(t, Starred):
        collect_target_names(t.value, out)


# Expression node classes, used by passes that rewrite sub-expressions.
EXPR_TYPES: dict[type, int] = {}
for _cls in (Name, Const, JoinedStr, FormattedValue, Tuple, List, SetDisplay, DictDisplay, Starred, BinOp,
             UnaryOp, BoolOp, Compare, Call, Attribute, Subscript, Slice, IfExp, Lambda, NamedExpr, ListComp,
             SetComp, DictComp, GeneratorExp, Yield, YieldFrom, Await, Temp):
    EXPR_TYPES[_cls] = 1

# Statements that contain other statements.
COMPOUND: dict[type, int] = {If: 1, While: 1, For: 1, Try: 1, With: 1, FunctionDef: 1, ClassDef: 1, Match: 1}
