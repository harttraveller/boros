"""Parsing of statements, blocks, and function and class definitions.

A module is a sequence of statements.  `statement` dispatches on the first
token of each one: a compound statement (if, for, while, try, with, def,
class, async, a decorator or match) has a method that parses its header and
its indented `suite`; anything else is a line of simple statements separated
by semicolons, each dispatched by `small_stmt`.  The dispatch tables
COMPOUND_STATEMENTS and SIMPLE_STATEMENTS at the end of the module map each
statement keyword to the method that parses it.

Statements that bind names (assignments, imports, def, class, global,
nonlocal, del, `except ... as`, function parameters) record those names in
the current Scope.  The compiler uses these facts to decide whether each
name is local, global or a closure variable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..core_types import Token
from ..syntax import (
    AnnAssign,
    Arguments,
    Assert,
    Assign,
    Attribute,
    AugAssign,
    Break,
    ClassDef,
    Const,
    Continue,
    Delete,
    ExceptHandler,
    Expression,
    ExprStmt,
    For,
    FunctionDef,
    Global,
    If,
    Import,
    ImportFrom,
    Keyword,
    Lambda,
    List,
    Module,
    Name,
    NamedExpr,
    Nonlocal,
    Pass,
    Raise,
    Return,
    Scope,
    Starred,
    Statement,
    Subscript,
    Try,
    Tuple,
    TypeAlias,
    While,
    With,
    WithItem,
    collect_target_names,
)
from .base import AUG_OPS, EXPR_END, ParserBase


class StatementParser(ParserBase):
    """Parsing of statements, blocks, and function and class definitions (a mixin of boros.parser.Parser)."""

    # -- modules, statements and blocks ----------------------------------------

    def parse_module(self) -> Module:
        """Parse a whole source file into a Module (blank lines are skipped).

        `from __future__` imports are allowed only in the prologue of the
        module: before any statement other than a docstring and such imports."""
        body: list[Statement] = []
        prologue: bool = True
        while self.tok[0] != 'EOF':
            if self.tok[0] == 'NEWLINE':
                self.advance()
                continue
            self.future_ok = prologue and self.tok[1] == 'from'
            stmts: list[Statement] = self.statement()
            prologue = prologue and in_prologue(body, stmts)
            body.extend(stmts)
        return Module(1, body, self.scope)

    def statement(self) -> list[Statement]:
        """Parse one statement, or one line of `;`-separated simple statements."""
        t: Token = self.tok
        if t[0] == 'NAME':
            parse: Callable[[StatementParser], Statement] | None = COMPOUND_STATEMENTS.get(t[1])
            if parse is not None:
                return [parse(self)]
            if t[1] == 'match' and self.looks_like_match():
                return [self.match_stmt()]
        elif t[1] == '@' and t[0] == 'OP':
            return [self.decorated()]
        elif t[0] == 'INDENT':
            self.error('unexpected indent', None, IndentationError)
        return self.simple_stmts()

    def simple_stmts(self) -> list[Statement]:
        """Parse `stmt; stmt; ...` up to and including the end of the line."""
        stmts: list[Statement] = [self.small_stmt()]
        while self.accept(';'):
            if self.tok[0] == 'NEWLINE':
                break
            stmts.append(self.small_stmt())
        if self.tok[0] != 'NEWLINE':
            self.error()
        self.advance()
        return stmts

    def suite(self) -> list[Statement]:
        """Parse the body of a compound statement.

        The body is either simple statements on the same line as the header
        or, after a NEWLINE, an INDENT token, statements and a DEDENT token
        (the lexer turns changes of indentation into INDENT and DEDENT)."""
        if self.tok[0] != 'NEWLINE':
            return self.simple_stmts()
        self.advance()
        if self.tok[0] != 'INDENT':
            self.error('expected an indented block', None, IndentationError)
        self.advance()
        body: list[Statement] = []
        while self.tok[0] != 'DEDENT' and self.tok[0] != 'EOF':
            body.extend(self.statement())
        if self.tok[0] == 'DEDENT':
            self.advance()
        return body

    def optional_suite(self, keyword: str) -> list[Statement]:
        """Parse an optional `keyword: suite` clause such as `else:` or `finally:`; [] if absent."""
        if self.tok[1] != keyword:
            return []
        self.advance()
        self.expect(':')
        return self.suite()

    def scoped_suite(self, scope: Scope) -> list[Statement]:
        """Parse the body of a function or class with `scope` as the current
        scope (and outside any loop: `break` cannot leave a function)."""
        saved: Scope = self.scope
        saved_loops: int = self.loops
        self.scope = scope
        self.loops = 0
        body: list[Statement] = self.suite()
        self.scope = saved
        self.loops = saved_loops
        return body

    def loop_body(self) -> list[Statement]:
        """Parse the body of a loop, where `break` and `continue` may appear."""
        self.loops += 1
        body: list[Statement] = self.suite()
        self.loops -= 1
        return body

    # -- simple statements -------------------------------------------------------

    def small_stmt(self) -> Statement:
        """Parse one simple statement: a keyword statement, a type alias, or an expression statement."""
        t: Token = self.tok
        if t[0] == 'NAME':
            parse: Callable[[StatementParser], Statement] | None = SIMPLE_STATEMENTS.get(t[1])
            if parse is not None:
                return parse(self)
            # `type` is a soft keyword: `type X = ...` is an alias, `type = 5` an assignment
            if t[1] == 'type' and self.peek()[0] == 'NAME' and self.peek(2)[1] in ('=', '['):
                return self.type_alias()
        return self.expr_stmt()

    def pass_stmt(self) -> Pass:
        """Parse `pass`."""
        return Pass(self.advance()[2])

    def break_stmt(self) -> Break:
        """Parse `break`, which must be inside a loop."""
        if self.loops == 0:
            self.error("'break' outside loop")
        return Break(self.advance()[2])

    def continue_stmt(self) -> Continue:
        """Parse `continue`, which must be inside a loop."""
        if self.loops == 0:
            self.error("'continue' not properly in loop")
        return Continue(self.advance()[2])

    def return_stmt(self) -> Return:
        """Parse `return` or `return value`."""
        line: int = self.advance()[2]
        value: Expression | None = None
        if self.tok[0] != 'NEWLINE' and self.tok[1] not in EXPR_END:
            value = self.testlist_star_expr()
        return Return(line, value)

    def raise_stmt(self) -> Raise:
        """Parse `raise`, `raise exc` or `raise exc from cause`."""
        line: int = self.advance()[2]
        exc: Expression | None = None
        cause: Expression | None = None
        if self.tok[0] != 'NEWLINE' and self.tok[1] != ';':
            exc = self.test()
            if self.accept('from'):
                cause = self.test()
        return Raise(line, exc, cause)

    def global_stmt(self) -> Global:
        """Parse `global a, b`, declaring the names global in the current scope."""
        line: int = self.advance()[2]
        names: list[str] = self.declared_names()
        for x in names:
            self.check_declaration(x, 'global', line)
            self.scope.globals.add(x)
            self.scope.decl_lines.setdefault(x, line)
        return Global(line, names)

    def nonlocal_stmt(self) -> Nonlocal:
        """Parse `nonlocal a, b`, declaring the names as belonging to an enclosing function.

        (That an enclosing function binds them is checked by the compiler.)"""
        line: int = self.advance()[2]
        if self.scope.kind == 'module':
            self.error('nonlocal declaration not allowed at module level', ('NAME', 'nonlocal', line))
        names: list[str] = self.declared_names()
        for x in names:
            self.check_declaration(x, 'nonlocal', line)
            self.scope.nonlocals.add(x)
            self.scope.decl_lines.setdefault(x, line)
        return Nonlocal(line, names)

    def check_declaration(self, x: str, what: str, line: int) -> None:
        """CPython's checks of name `x` declared `what` ('global' or
        'nonlocal') at `line`: it must not be a parameter, nor be used or
        assigned (other than by an import) earlier in the scope, nor be
        declared the other way too."""
        sc: Scope = self.scope
        msg: str | None = None
        if x in sc.params:
            msg = f"name '{x}' is parameter and {what}"
        elif sc.loads.count(x) > sc.unloads.count(x):
            msg = f"name '{x}' is used prior to {what} declaration"
        elif x in sc.assigned and x not in sc.imported:
            msg = f"name '{x}' is assigned to before {what} declaration"
        elif x in (sc.nonlocals if what == 'global' else sc.globals):
            msg = f"name '{x}' is nonlocal and global"
            line = sc.decl_lines[x]
        if msg is not None:
            self.error(msg, ('NAME', x, line))

    def declared_names(self) -> list[str]:
        """Parse the names of a global or nonlocal statement, mangling private names."""
        names: list[str] = [self.mangle(self.expect_name())]
        while self.accept(','):
            names.append(self.mangle(self.expect_name()))
        return names

    def del_stmt(self) -> Delete:
        """Parse `del a, b[0], c.d`; deleted names are recorded in the scope."""
        line: int = self.advance()[2]
        targets: list[Expression] = self.exprlist(True)
        for x in targets:
            self.record_target(x, True, 'delete')
            collect_target_names(x, self.scope.deleted)
        return Delete(line, targets)

    def assert_stmt(self) -> Assert:
        """Parse `assert test` or `assert test, message`."""
        line: int = self.advance()[2]
        test: Expression = self.test()
        msg: Expression | None = None
        if self.accept(','):
            msg = self.test()
        return Assert(line, test, msg)

    def type_alias(self) -> Assign:
        """Parse `type X[params] = value` (PEP 695) into the assignment of a
        TypeAlias to X.  The value is evaluated lazily, by a function of
        the type parameters, so it is parsed as the body of a lambda."""
        line: int = self.advance()[2]
        name: str = self.mangle(self.expect_name())
        params: list[tuple[str, str]] = self.type_params() if self.accept('[') else []
        self.expect('=')
        names: list[str] = [p[1] for p in params]
        scope: Scope = Scope('function', name, self.scope)
        scope.assigned.update(names)
        saved: Scope = self.scope
        self.scope = scope
        value: Expression = self.test()
        self.scope = saved
        compute: Lambda = Lambda(line, Arguments(line, [], names, [], None, [], [], None, []), value, scope)
        self.scope.assigned.add(name)
        return Assign(line, [Name(line, name)], TypeAlias(line, name, params, compute))

    def type_params(self) -> list[tuple[str, str]]:
        """Parse the type parameters of a type alias, after the '[': a list
        of (kind, name) with kind '' for `T`, '*' for `*Ts` and '**' for
        `**P`.  Bounds, constraints and defaults are parsed but discarded."""
        params: list[tuple[str, str]] = []
        while self.tok[1] != ']':
            kind: str = ''
            if self.tok[1] == '*' or self.tok[1] == '**':
                kind = self.advance()[1]
            params.append((kind, self.expect_name()))
            if self.accept(':'):
                self.test()
            if self.accept('='):
                self.test()
            if not self.accept(','):
                break
        self.expect(']')
        return params

    # -- expression statements and assignments ------------------------------------

    def expr_stmt(self) -> Statement:
        """Parse an expression statement or an assignment (`=`, augmented `+=`, or annotated `x: T = v`)."""
        line: int = self.tok[2]
        start: Token = self.tok
        paren: bool = start[1] == '('
        first: Expression = self.yield_expr() if self.tok[1] == 'yield' else self.testlist_star_expr()
        t: Token = self.tok
        if t[1] == '=':
            return self.assignment(line, first)
        if t[1] in AUG_OPS and t[0] == 'OP':
            return self.augmented_assignment(line, first, AUG_OPS[t[1]])
        if type(first) is NamedExpr and start[1] != '(':
            self.error('invalid syntax', start)  # an assignment expression statement must be parenthesized
        if t[1] == ':' and t[0] == 'OP':
            return self.annotated_assignment(line, first, type(first) is Name and not paren)
        return ExprStmt(line, first)

    def assigned_value(self) -> Expression:
        """Parse an expression list or a yield expression, either side of an assignment."""
        if self.tok[1] == 'yield':
            return self.yield_expr()
        return self.testlist_star_expr()

    def assignment(self, line: int, first: Expression) -> Assign:
        """Parse the rest of `a = b = value`; the last item is the value, the others are targets."""
        targets: list[Expression] = [first]
        while self.accept('='):
            targets.append(self.assigned_value())
        value: Expression = targets.pop()
        if type(value) is Starred:
            self.error("can't use starred expression here")
        for t in targets:
            self.record_target(t)
        return Assign(line, targets, value)

    def augmented_assignment(self, line: int, target: Expression, op: str) -> AugAssign:
        """Parse the rest of `target op= value`, where `op` is the binary operator (`+` for `+=`)."""
        self.advance()
        tt: type = type(target)
        if tt is not Name and tt is not Attribute and tt is not Subscript:
            self.error(f"'{type(target).__name__}' is an illegal expression for augmented assignment")
        value: Expression = self.assigned_value()
        self.record_target(target)
        return AugAssign(line, target, op, value)

    def annotated_assignment(self, line: int, target: Expression, simple: bool) -> AnnAssign:
        """Parse the rest of `target: annotation` or `target: annotation = value`.
        `simple` says whether the target is a name without parentheses."""
        tt: type = type(target)
        if tt is not Name and tt is not Attribute and tt is not Subscript:
            self.error(f'only single target (not {tt.__name__.lower()}) can be annotated'
                       if tt is Tuple or tt is List else 'illegal target for annotation')
        self.advance()
        if type(target) is Tuple or type(target) is List:
            self.error(f'only single target (not {type(target).__name__.lower()}) can be annotated')
        if type(target) is not Name and type(target) is not Attribute and type(target) is not Subscript:
            self.error('illegal target for annotation')
        # (the annotations of a function's local variables are never evaluated)
        ann: Expression = self.test() if self.scope.kind == 'function' else self.annotation()
        value: Expression | None = None
        if self.accept('='):
            value = self.assigned_value()
        self.record_target(target)
        return AnnAssign(line, target, ann, value, simple)

    def annotation(self) -> Expression:
        """Parse an annotation.  Under `from __future__ import annotations` it
        is never evaluated: it becomes the string of its source text."""
        e: Expression = self.test()
        if self.future_annotations:
            from .unparse import unparse
            return Const(e.line, unparse(e))
        return e

    # -- imports -----------------------------------------------------------------

    def import_stmt(self) -> Import:
        """Parse `import a.b.c as d, e`.

        Without `as`, the statement binds the first component of the dotted
        name (`import a.b` binds `a`)."""
        line: int = self.advance()[2]
        names: list[tuple[str, str | None]] = []
        while True:
            dotted: str = self.dotted_name()
            asname: str | None = None
            if self.accept('as'):
                asname = self.expect_name()
            bound: str = asname or dotted.split('.')[0]
            self.scope.assigned.add(bound)
            self.scope.imported.add(bound)
            names.append((dotted, asname))
            if not self.accept(','):
                break
        return Import(line, names)

    def dotted_name(self) -> str:
        """Parse a dotted module name such as `a.b.c`."""
        parts: list[str] = [self.expect_name()]
        while self.tok[1] == '.':
            self.advance()
            parts.append(self.expect_name())
        return '.'.join(parts)

    def from_stmt(self) -> ImportFrom:
        """Parse `from module import names`, `from . import names` or `from module import *`.

        The number of leading dots is the relative import level (the lexer
        produces `...` as one token, which counts three)."""
        line: int = self.advance()[2]
        level: int = 0
        while self.tok[1] == '.' or self.tok[1] == '...':
            level += len(self.tok[1])
            self.advance()
        module: str | None = None
        if self.tok[1] != 'import':
            module = self.dotted_name()
        self.expect('import')
        if self.tok[1] == '*' and self.scope.kind != 'module':
            self.error('import * only allowed at module level', self.tok)
        names: list[tuple[str, str | None]] = [('*', None)] if self.accept('*') else self.import_as_names()
        if module == '__future__' and level == 0:
            self.check_future(names)
            if ('annotations', None) in names:
                self.future_annotations = True
        return ImportFrom(line, module, names, level)

    def check_future(self, names: list[tuple[str, str | None]]) -> None:
        """Check a `from __future__ import` statement as CPython's compiler
        does: it must be at the start of the module and name known features."""
        if not self.future_ok:
            self.error('from __future__ imports must occur at the beginning of the file')
        for name, _ in names:
            if name == 'braces':
                self.error('not a chance')
            if name not in FUTURE_FEATURES:
                self.error(f'future feature {name} is not defined')

    def import_as_names(self) -> list[tuple[str, str | None]]:
        """Parse `a as b, c` after `from module import`, optionally in parentheses."""
        paren: bool = self.accept('(')
        names: list[tuple[str, str | None]] = []
        while True:
            if paren and self.tok[1] == ')':
                break
            name: str = self.expect_name()
            asname: str | None = None
            if self.accept('as'):
                asname = self.expect_name()
            self.scope.assigned.add(asname or name)
            self.scope.imported.add(asname or name)
            names.append((name, asname))
            if not self.accept(','):
                break
        if paren:
            self.expect(')')
        return names

    # -- compound statements -------------------------------------------------------

    def if_stmt(self) -> If:
        """Parse an if statement.  `elif` becomes a nested If in the else branch."""
        line: int = self.advance()[2]
        test: Expression = self.namedexpr_test()
        self.expect(':')
        body: list[Statement] = self.suite()
        if self.tok[1] == 'elif':
            orelse: list[Statement] = [self.if_stmt()]
        else:
            orelse = self.optional_suite('else')
        return If(line, test, body, orelse)

    def while_stmt(self) -> While:
        """Parse a while loop with its optional `else:` clause."""
        line: int = self.advance()[2]
        test: Expression = self.namedexpr_test()
        self.expect(':')
        body: list[Statement] = self.loop_body()
        orelse: list[Statement] = self.optional_suite('else')
        return While(line, test, body, orelse)

    def for_stmt(self, is_async: bool) -> For:
        """Parse a for loop (`async for` when `is_async`) with its optional `else:` clause."""
        line: int = self.advance()[2]
        target: Expression = self.target_list()
        self.record_target(target)
        self.expect('in')
        it: Expression = self.testlist_star_expr()
        self.expect(':')
        body: list[Statement] = self.loop_body()
        orelse: list[Statement] = self.optional_suite('else')
        return For(line, target, it, body, orelse, is_async)

    def try_stmt(self) -> Try:
        """Parse a try statement with its except, else and finally clauses."""
        line: int = self.advance()[2]
        self.expect(':')
        body: list[Statement] = self.suite()
        handlers: list[ExceptHandler] = []
        star: bool = self.tok[1] == 'except' and self.peek()[1] == '*'
        while self.tok[1] == 'except':
            if (self.peek()[1] == '*') != star:
                self.error("cannot have both 'except' and 'except*' on the same 'try'")
            handlers.append(self.except_handler())
        orelse: list[Statement] = self.optional_suite('else')
        finalbody: list[Statement] = self.optional_suite('finally')
        if not handlers and not finalbody:
            self.error("expected 'except' or 'finally' block")
        return Try(line, body, handlers, orelse, finalbody, star)

    def except_handler(self) -> ExceptHandler:
        """Parse one `except [type [as name]]:` clause and its body.

        `except*` (which needs a type) is parsed like `except`, and
        `except A, B:` like `except (A, B):`.  The bound name is recorded as
        deleted too, because Python unbinds it when the handler ends."""
        line: int = self.advance()[2]
        if self.tok[1] == '*':
            self.advance()
            if self.tok[1] == ':':
                self.error('expected one or more exception types')
        typ: Expression | None = None
        name: str | None = None
        if self.tok[1] != ':':
            typ = self.test()
            if self.tok[1] == ',':
                elts: list[Expression] = [typ]
                while self.accept(','):
                    elts.append(self.test())
                typ = Tuple(line, elts)
            if self.accept('as'):
                name = self.mangle(self.expect_name())
                self.scope.assigned.add(name)
                self.scope.deleted.add(name)
        self.expect(':')
        return ExceptHandler(line, typ, name, self.suite())

    def with_stmt(self, is_async: bool) -> With:
        """Parse a with statement (`async with` when `is_async`)."""
        line: int = self.advance()[2]
        items: list[WithItem] | None = None
        if self.tok[1] == '(':
            items = self.parenthesized_with_items()
        if items is None:
            items = [self.with_item()]
            while self.accept(','):
                items.append(self.with_item())
        for it in items:
            if it.target is not None:
                self.record_target(it.target)
        self.expect(':')
        body: list[Statement] = self.suite()
        return With(line, items, body, is_async)

    def parenthesized_with_items(self) -> list[WithItem] | None:
        """Try to parse the parenthesized form `with (a as b, c as d):`.

        A parenthesis after `with` may also start an ordinary expression, as
        in `with (a, b)[0]:`, so on failure this backtracks to the parenthesis
        and returns None."""
        save: int = self.pos
        try:
            self.advance()
            items: list[WithItem] = []
            while self.tok[1] != ')':
                items.append(self.with_item())
                if not self.accept(','):
                    break
            self.expect(')')
            if self.tok[1] != ':':
                raise SyntaxError('not a parenthesized with')
        except SyntaxError:
            self.pos = save
            self.tok = self.toks[save]
            return None
        return items

    def with_item(self) -> WithItem:
        """Parse one `expression [as target]` item of a with statement."""
        line: int = self.tok[2]
        e: Expression = self.test()
        target: Expression | None = None
        if self.accept('as'):
            target = self.target()
        return WithItem(line, e, target)

    def decorated(self) -> Statement:
        """Parse decorators (`@expr` lines) and the def, async def or class they decorate."""
        decorators: list[Expression] = []
        while self.tok[1] == '@':
            self.advance()
            decorators.append(self.namedexpr_test())
            if self.tok[0] != 'NEWLINE':
                self.error()
            self.advance()
        v: Any = self.tok[1]
        if v == 'def':
            return self.funcdef(decorators, False)
        if v == 'class':
            return self.classdef(decorators)
        if v == 'async':
            return self.async_stmt(decorators)
        self.error()

    def async_stmt(self, decorators: list[Expression]) -> Statement:
        """Parse `async def`, `async for` or `async with` (only `async def` may be decorated)."""
        self.advance()
        v: Any = self.tok[1]
        if v == 'def':
            return self.funcdef(decorators, True)
        if decorators:
            self.error()
        if v == 'for':
            return self.for_stmt(True)
        if v == 'with':
            return self.with_stmt(True)
        self.error()

    # -- function and class definitions --------------------------------------------

    def funcdef(self, decorators: list[Expression], is_async: bool) -> FunctionDef:
        """Parse a function definition; its body is parsed in a new function scope.

        Type parameters are parsed (to validate them) but discarded.  The
        type parameters are then unbound names, so the annotations of such a
        generic function are discarded too instead of being evaluated."""
        line: int = self.advance()[2]
        name: str = self.mangle(self.expect_name())
        generic: bool = self.tok[1] == '['
        if generic:
            self.skip_type_params()
        self.scope.assigned.add(name)
        scope: Scope = Scope('function', name, self.scope)
        scope.is_async = is_async
        self.expect('(')
        args: Arguments = self.parameters(')', True, scope)
        self.expect(')')
        if self.accept('->'):
            args.annotations.append(('return', self.annotation()))
        if generic:
            args.annotations = []
        self.expect(':')
        body: list[Statement] = self.scoped_suite(scope)
        return FunctionDef(line, name, args, body, decorators, scope, is_async)

    def skip_type_params(self) -> None:
        """Skip a bracketed PEP 695 type parameter list such as `[T, U: int]`."""
        depth: int = 0
        while True:
            v: Any = self.advance()[1]
            if v == '[':
                depth += 1
            elif v == ']':
                depth -= 1
                if depth == 0:
                    return

    def parameters(self, closer: str, annotations: bool, scope: Scope) -> Arguments:
        """Parse a parameter list up to (not including) `closer`: `)` for def, `:` for lambda.

        Handles positional-only parameters (before `/`), defaults, `*args`,
        keyword-only parameters (after `*` or `*args`) and `**kwargs`.  The
        parameter names are bound in `scope`, the scope of the new function.
        `annotations` is False for lambdas, whose parameters cannot be annotated."""
        posonly: list[str] = []
        args: list[str] = []
        defaults: list[Expression] = []
        vararg: str | None = None
        kwonly: list[str] = []
        kw_defaults: list[Expression | None] = []
        kwarg: str | None = None
        star: bool = False
        anns: list[tuple[str, Expression]] = []
        while self.tok[1] != closer:
            if kwarg is not None:
                self.error('arguments cannot follow var-keyword argument')
            if self.accept('/'):
                self.check_slash(posonly, args, star)
                posonly = args
                args = []
            elif self.accept('*'):
                if star:
                    self.error('* argument may appear only once')
                star = True
                if self.tok[0] == 'NAME':
                    vararg = self.parameter_name(annotations, anns)
            elif self.accept('**'):
                kwarg = self.parameter_name(annotations, anns)
            else:
                name: str = self.parameter_name(annotations, anns)
                default: Expression | None = self.parameter_default()
                if star:
                    kwonly.append(name)
                    kw_defaults.append(default)
                else:
                    args.append(name)
                    self.add_positional_default(default, defaults)
            if not self.accept(','):
                break
        result: Arguments = Arguments(self.tok[2], posonly, args, defaults, vararg, kwonly, kw_defaults, kwarg,
                                      anns)
        self.check_parameters(result, star)
        bind_parameters(scope, result)
        return result

    def check_slash(self, posonly: list[str], args: list[str], star: bool) -> None:
        """Check the position of a `/` in a parameter list, given the
        positional-only parameters before an earlier `/`, the parameters
        since, and whether a `*` came before."""
        if posonly:
            self.error('/ may appear only once')
        if star:
            self.error('/ must be ahead of *')
        if not args:
            self.error('at least one argument must precede /')

    def check_parameters(self, a: Arguments, star: bool) -> None:
        """Check a complete parameter list: a bare `*` must be followed by a
        keyword-only parameter, and no name may appear twice."""
        if star and a.vararg is None and not a.kwonly:
            self.error('named arguments must follow bare *')
        seen: set[str] = set()
        for x in parameter_names(a):
            if x in seen:
                self.error(f"duplicate argument '{x}' in function definition")
            seen.add(x)

    def parameter_name(self, annotations: bool, anns: list[tuple[str, Expression]]) -> str:
        """Parse a parameter name and, if allowed, its annotation, which is
        appended to anns."""
        name: str = self.mangle(self.expect_name())
        if annotations and self.accept(':'):
            anns.append((name, self.annotation()))
        return name

    def parameter_default(self) -> Expression | None:
        """Parse the `= default` of a parameter, if present."""
        if self.accept('='):
            return self.test()
        return None

    def add_positional_default(self, default: Expression | None, defaults: list[Expression]) -> None:
        """Record the default of a positional parameter.

        Defaults belong to the last positional parameters, so once one
        parameter has a default, all the following ones must have one too."""
        if default is not None:
            defaults.append(default)
        elif defaults:
            self.error('parameter without a default follows parameter with a default')

    def classdef(self, decorators: list[Expression]) -> ClassDef:
        """Parse a class definition; its body is parsed in a new class scope.

        The bases and keywords (such as `metaclass=`) are parsed like call arguments."""
        line: int = self.advance()[2]
        name: str = self.mangle(self.expect_name())
        if self.tok[1] == '[':
            self.skip_type_params()
        self.scope.assigned.add(name)
        bases: list[Expression] = []
        keywords: list[Keyword] = []
        if self.accept('('):
            bases, keywords = self.call_args()
        self.expect(':')
        scope: Scope = Scope('class', name, self.scope)
        body: list[Statement] = self.scoped_suite(scope)
        return ClassDef(line, name, bases, keywords, body, decorators, scope)


def bind_parameters(scope: Scope, a: Arguments) -> None:
    """Record the parameter names of a function as assigned in its scope,
    and as its parameters (for the checks of global and nonlocal)."""
    names: list[str] = parameter_names(a)
    scope.assigned.update(names)
    scope.params = set(names)


def parameter_names(a: Arguments) -> list[str]:
    """All the parameter names of a parameter list, in order."""
    names: list[str] = a.posonly + a.args
    if a.vararg is not None:
        names.append(a.vararg)
    names.extend(a.kwonly)
    if a.kwarg is not None:
        names.append(a.kwarg)
    return names


def in_prologue(body: list[Statement], stmts: list[Statement]) -> bool:
    """Do the statements `stmts`, which follow `body` at the top of a
    module, still belong to its prologue, where `from __future__` imports
    are allowed: a docstring first, then only such imports?"""
    for s in stmts:
        if type(s) is ImportFrom and s.module == '__future__' and s.level == 0:
            continue
        if body or s is not stmts[0] or type(s) is not ExprStmt or type(s.value) is not Const \
                or type(s.value.value) is not str:
            return False
    return True


# The features `from __future__ import` accepts.
FUTURE_FEATURES: dict[str, int] = {
    'nested_scopes': 1, 'generators': 1, 'division': 1, 'absolute_import': 1, 'with_statement': 1,
    'print_function': 1, 'unicode_literals': 1, 'barry_as_FLUFL': 1, 'generator_stop': 1, 'annotations': 1,
}


# Compound statements by their first keyword.  (`match` is a soft keyword and
# decorators start with `@`, so `statement` recognizes those itself.)
COMPOUND_STATEMENTS: dict[str, Callable[[StatementParser], Statement]] = {
    'if': StatementParser.if_stmt,
    'for': lambda p: p.for_stmt(False),
    'while': StatementParser.while_stmt,
    'def': lambda p: p.funcdef([], False),
    'class': lambda p: p.classdef([]),
    'try': StatementParser.try_stmt,
    'with': lambda p: p.with_stmt(False),
    'async': lambda p: p.async_stmt([]),
}

# Simple statements that start with a keyword.  (`type` is a soft keyword, so
# `small_stmt` recognizes type aliases itself.)
SIMPLE_STATEMENTS: dict[str, Callable[[StatementParser], Statement]] = {
    'pass': StatementParser.pass_stmt,
    'return': StatementParser.return_stmt,
    'break': StatementParser.break_stmt,
    'continue': StatementParser.continue_stmt,
    'raise': StatementParser.raise_stmt,
    'global': StatementParser.global_stmt,
    'nonlocal': StatementParser.nonlocal_stmt,
    'del': StatementParser.del_stmt,
    'assert': StatementParser.assert_stmt,
    'import': StatementParser.import_stmt,
    'from': StatementParser.from_stmt,
}
