"""The parser: source text to a syntax tree (see `syntax`).

`parse` runs the lexer (`boros.lexer.tokenize`) and then a hand-written
recursive-descent parser over the tokens: one method per grammar rule,
each consuming the tokens of its construct and returning a syntax node.
The parser is assembled from mixins, one per area of the grammar:

- `base.ParserBase`: the token cursor (advance, accept, expect, error) and
  scope bookkeeping shared by all the others;
- `statements.StatementParser`: simple and compound statements, function
  and class definitions, parameter lists;
- `expressions.ExpressionParser`: expressions, by precedence climbing;
- `patterns.PatternParser`: the `match` statement and its patterns;
- `strings.StringParser`: string literals and f-strings.

Besides the tree, the parser records in each `Scope` which names are
assigned, declared global or nonlocal, and so on; the compiler uses this
to decide whether a name is local, a closure cell or a global.
"""

from __future__ import annotations

import sys

from ..lexer import tokenize
from ..syntax import Call, Const, Expression, ExprStmt, For, If, Match, Module, Scope, Statement, Try, While, With
from .expressions import ExpressionParser
from .patterns import PatternParser
from .statements import StatementParser
from .strings import StringParser


class Parser(StatementParser, PatternParser, ExpressionParser, StringParser):
    """The complete recursive-descent parser, combining all the mixins."""


def parse(src: str, filename: str = '<string>') -> Module:
    """Parse the source of a module (for exec, import or the main program)
    into a syntax tree."""
    scope: Scope = Scope('module', '<module>', None)
    p: Parser = Parser(tokenize(src, filename), filename, scope)
    return p.parse_module()


def parse_eval(src: str, filename: str) -> Module:
    """Parse the source given to eval(): a single expression list, returned
    as a module whose only statement is that expression."""
    scope: Scope = Scope('module', '<module>', None)
    p: Parser = Parser(tokenize(src.strip(' \t\n'), filename), filename, scope)
    while p.tok[0] == 'NEWLINE':
        p.advance()
    e: Expression = p.testlist_star_expr()
    while p.tok[0] == 'NEWLINE':
        p.advance()
    if p.tok[0] != 'EOF':
        p.error()
    return Module(1, [ExprStmt(1, e)], scope)


def parse_single(src: str, filename: str) -> Module:
    """Parse the source given to compile(..., 'single'), as the interactive
    interpreter does: exactly one statement (a compound statement, or one
    line of simple statements), whose expression statements print their
    values through sys.displayhook."""
    scope: Scope = Scope('module', '<module>', None)
    p: Parser = Parser(tokenize(src, filename), filename, scope)
    while p.tok[0] == 'NEWLINE':
        p.advance()
    body: list[Statement] = []
    if p.tok[0] != 'EOF':
        p.future_ok = p.tok[1] == 'from'
        body = p.statement()
    while p.tok[0] == 'NEWLINE':
        p.advance()
    if p.tok[0] != 'EOF':
        p.error('multiple statements found while compiling a single statement')
    echo_expressions(body)
    return Module(1, body, scope)


def echo_expressions(stmts: list[Statement]) -> None:
    """Make the expression statements in stmts (and in the blocks of their
    compound statements, but not in function or class bodies) display
    their values, as in the interactive interpreter."""
    for i, s in enumerate(stmts):
        if type(s) is ExprStmt:
            stmts[i] = ExprStmt(s.line, Call(s.line, Const(s.line, interactive_echo), [s.value], []))
        else:
            for block in statement_blocks(s):
                echo_expressions(block)


def statement_blocks(s: Statement) -> list[list[Statement]]:
    """The blocks of statements directly inside compound statement s, other
    than a function or class body."""
    if type(s) is If or type(s) is While or type(s) is For:
        return [s.body, s.orelse]
    if type(s) is With:
        return [s.body]
    if type(s) is Try:
        return [s.body, *[h.body for h in s.handlers], s.orelse, s.finalbody]
    if type(s) is Match:
        return [c.body for c in s.cases]
    return []


def interactive_echo(value: object) -> None:
    """Display the value of an expression statement compiled in 'single'
    mode: sys.displayhook prints its repr (unless it is None) and stores
    it in builtins._."""
    sys.displayhook(value)
