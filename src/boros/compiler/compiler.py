"""The Compiler class: syntax tree to a tree of Python closures.

A `Compiler` holds the state needed while compiling one module (its globals
dict, file name and the stack of enclosing scopes), resolves variable names,
and dispatches every syntax node to the `compile_*` function for its type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..syntax import (
    AnnAssign,
    Assert,
    Assign,
    Attribute,
    AugAssign,
    Await,
    BinOp,
    BoolOp,
    Break,
    Call,
    ClassDef,
    Compare,
    Const,
    Continue,
    Delete,
    DictComp,
    DictDisplay,
    Expression,
    ExprStmt,
    For,
    FormattedValue,
    FunctionDef,
    GeneratorExp,
    Global,
    If,
    IfExp,
    Import,
    ImportFrom,
    JoinedStr,
    Lambda,
    List,
    ListComp,
    Match,
    Name,
    NamedExpr,
    Nonlocal,
    Pass,
    Raise,
    Return,
    SetComp,
    SetDisplay,
    Slice,
    Starred,
    Statement,
    Subscript,
    Temp,
    Try,
    Tuple,
    TypeAlias,
    UnaryOp,
    While,
    With,
    Yield,
    YieldFrom,
)
from .calls import compile_call
from .comprehensions import compile_dictcomp, compile_genexp, compile_listcomp, compile_setcomp
from .definitions import compile_classdef, compile_funcdef, compile_lambda, compile_type_alias
from .expressions import (
    compile_attribute,
    compile_await,
    compile_dict,
    compile_formattedvalue,
    compile_ifexp,
    compile_joinedstr,
    compile_list,
    compile_namedexpr,
    compile_set,
    compile_slice,
    compile_starred,
    compile_subscript,
    compile_tuple,
    compile_yield,
)
from .names import compile_const, compile_name, compile_temp
from .operators import compile_binop, compile_boolop, compile_compare, compile_unaryop
from .patterns import compile_match
from .scopes import CLASSNS, FREE, GLOBAL, GLOBAL_RES, LOCAL, LOCAL_RES, MAPPED
from .statements import (
    compile_annassign,
    compile_assert,
    compile_assign,
    compile_augassign,
    compile_break,
    compile_continue,
    compile_delete,
    compile_expr_stmt,
    compile_for,
    compile_if,
    compile_import,
    compile_importfrom,
    compile_pass,
    compile_raise,
    compile_return,
    compile_try,
    compile_while,
    compile_with,
    module_body,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core_types import ExprFn, Frame, StmtFn
    from ..runtime.objects import Signal
    from ..syntax import Scope


class Compiler:
    """Compiles the syntax tree of one module into closures.

    The compiler walks the tree once.  For each node it asks a `compile_*`
    function (chosen by node type from EXPR_COMPILERS / STMT_COMPILERS) to
    build a closure; those functions call back into `expr` and `stmt` for
    child nodes.  Name resolution happens here, at compile time, so the
    closures already know whether a variable is local, global or free and
    how many frames up it lives.

    Attributes:
        g: the module's globals dict; global loads and stores use it directly.
        filename: the source file name, for error messages and tracebacks.
        stack: the scopes enclosing the code being compiled, innermost last
            (module, then functions, classes and comprehensions).
        code_name: the name of the function (or class or '<module>') being
            compiled, recorded in traceback entries.
        ntemps: a counter for naming temporary frame slots (see new_temp).
    """

    g: Frame
    filename: str
    stack: list[Scope]
    code_name: str
    ntemps: int

    def __init__(self, g: Frame, filename: str, scope: Scope) -> None:
        self.g = g
        self.filename = filename
        self.stack = [scope]
        self.code_name = "<module>"
        self.ntemps = 0

    # -- name resolution -------------------------------------------------------

    def resolve(self, name: str) -> tuple[Signal, Any]:
        """Resolve a variable name in the innermost scope.

        Returns (kind, detail) with kind one of LOCAL, GLOBAL, FREE, CLASSNS
        or MAPPED (see scopes.py): for FREE and MAPPED the detail is the
        number of '.up' links to the frame or mapping holding the variable;
        for CLASSNS it is the resolution of the name outside the class body.
        Free variables are recorded in the scopes' freevars (see note_free).
        """
        stack: list[Scope] = self.stack
        sc: Scope = stack[-1]
        kind: str = sc.kind
        if kind == "module":
            return GLOBAL_RES
        if name in sc.globals:
            return GLOBAL_RES
        if kind == "class":
            if name in sc.nonlocals:
                return self.resolve_outer(name, len(stack) - 1)
            if name in sc.assigned:
                # bound in the class body: class namespace, then globals
                return (CLASSNS, GLOBAL_RES)
            return (CLASSNS, self.resolve_outer(name, len(stack) - 1))
        if name in sc.nonlocals:
            r: tuple[Signal, Any] = self.resolve_outer(name, len(stack) - 1)
            if r[0] is not FREE:
                raise SyntaxError(f"no binding for nonlocal '{name}' found")
            return r
        if name in sc.assigned:
            return LOCAL_RES
        return self.resolve_outer(name, len(stack) - 1)

    def resolve_outer(self, name: str, idx: int) -> tuple[Signal, Any]:
        """Resolve a name in the scopes enclosing stack[idx].

        Walks outwards counting function (and comprehension) frames; class
        bodies are skipped because their namespaces are not visible to
        nested functions.  The first enclosing function that assigns the
        name owns it (FREE, depth); otherwise the name is global.  But
        comprehensions inlined into exec()/eval() code with a separate
        locals mapping read that mapping (MAPPED, depth).
        """
        depth: int = 0
        i: int = idx - 1
        inlined: bool = self.stack[idx].inlined
        while i >= 0:
            s: Scope = self.stack[i]
            k: str = s.kind
            if k == "module":
                return GLOBAL_RES
            i -= 1
            if k == "class":
                if inlined and s.exec_locals:
                    return (MAPPED, depth + 1)
                continue
            inlined = inlined and s.inlined
            depth += 1
            if name in s.globals:
                return GLOBAL_RES
            if name in s.assigned and name not in s.nonlocals:
                self.note_free(name, idx, i + 1, depth)
                return (FREE, depth)
        return GLOBAL_RES

    def note_free(self, name: str, idx: int, owner: int, depth: int) -> None:
        """Record `name`, owned by the function at stack[owner], as a free
        variable of every function or comprehension from stack[idx] (whose
        frame is `depth` '.up' links from the owner's) out to the owner, for
        __closure__ and co_freevars.  Class bodies between them are not on
        the chain of frames."""
        j: int = idx
        while j > owner:
            s: Scope = self.stack[j]
            if s.kind != "class":
                s.freevars[name] = depth
            if s.kind != "class" or j == idx:
                depth -= 1
            j -= 1

    def local_name(self, n: Expression) -> str | None:
        """The name of n if it is a Name bound in the current function."""
        if type(n) is Name and self.resolve(n.id)[0] is LOCAL:
            return n.id
        return None

    def is_param(self, name: str) -> bool:
        """Whether `name` is a parameter of the current function that is never
        deleted.  Parameters are bound when the frame is created and stay
        bound, so loading them needs no unbound-variable check."""
        sc: Scope = self.stack[-1]
        return sc.kind == "function" and name in sc.params and name not in sc.deleted

    def operand(self, n: Expression) -> tuple[str | None, Any]:
        """Classify a simple operand that a parent closure can fetch inline.

        Returns (kind, name or value) with kind 'param', 'local', 'free1'
        (a free variable one frame up), 'global' or 'const', or (None, None)
        for anything else.  Compile functions use this to build specialized
        closures that read e.g. `fr[name]` directly instead of calling the
        operand's own closure.
        """
        if type(n) is Const:
            return "const", n.value
        if type(n) is Name:
            return self.name_operand(n.id)
        return None, None

    def name_operand(self, name: str) -> tuple[str | None, Any]:
        """The operand classification (see `operand`) of a variable name."""
        kind, depth = self.resolve(name)
        if kind is LOCAL:
            if self.is_param(name):
                return "param", name
            return "local", name
        if kind is FREE and depth == 1:
            return "free1", name
        if kind is GLOBAL and name != "__class__":
            return "global", name
        return None, None

    # -- information about the current scope -------------------------------------

    def function_depth(self) -> int | None:
        """The number of '.up' links from the current frame to the frame of the
        nearest enclosing function (comprehensions have frames of their own),
        or None when the code is not inside a function."""
        depth: int = 0
        for s in reversed(self.stack):
            if s.kind == "function":
                return depth
            if s.kind == "comp":
                depth += 1
            else:
                return None
        return None

    def closure_mode(self) -> int:
        """How a function or class defined here finds its enclosing frame:
        0 = the current frame (inside a function or comprehension),
        1 = the current frame's '.up' (inside a class body),
        2 = none (at module level, also in exec() code with separate locals)."""
        k: str = self.stack[-1].kind
        if k == "function" or k == "comp":
            return 0
        if k == "class" and not self.stack[-1].exec_locals:
            return 1
        return 2

    def new_temp(self) -> str:
        """A fresh frame key for a temporary value.  Keys start with '.' so
        they can never clash with a variable name."""
        self.ntemps += 1
        return f".t{self.ntemps}"

    def qualname(self, name: str) -> str:
        """The __qualname__ of a function or class called `name` defined in
        the current scope, e.g. 'Outer.method.<locals>.helper'.  Inlined
        comprehensions (and the top level of exec() code) add nothing, a
        generator expression adds '<genexpr>', and a name declared global
        is not qualified at all."""
        top: Scope = self.stack[-1]
        if top.kind != "module" and name in top.globals:
            return name
        parts: list[str] = []
        for s in self.stack:
            if s.kind == "module" or s.inlined or s.exec_locals:
                continue
            parts.append(s.name)
            if s.kind == "function":
                parts.append("<locals>")
        parts.append(name)
        return ".".join(parts)

    # -- dispatch ----------------------------------------------------------------

    def module_body(self, stmts: list[Statement]) -> StmtFn:
        """Compile the statements of a module into one closure."""
        return module_body(self, stmts)

    def expr(self, n: Expression) -> ExprFn:
        """Compile an expression into a closure `f(fr) -> value`."""
        return EXPR_COMPILERS[type(n)](self, n)

    def stmt(self, s: Statement) -> StmtFn:
        """Compile a statement into a closure `f(fr) -> None or a Signal`."""
        return STMT_COMPILERS[type(s)](self, s)


EXPR_COMPILERS: dict[type[Expression], Callable[[Compiler, Any], ExprFn]] = {
    Name: compile_name,
    Const: compile_const,
    Temp: compile_temp,
    BinOp: compile_binop,
    UnaryOp: compile_unaryop,
    BoolOp: compile_boolop,
    Compare: compile_compare,
    Call: compile_call,
    Attribute: compile_attribute,
    Subscript: compile_subscript,
    Slice: compile_slice,
    Tuple: compile_tuple,
    List: compile_list,
    SetDisplay: compile_set,
    DictDisplay: compile_dict,
    IfExp: compile_ifexp,
    NamedExpr: compile_namedexpr,
    JoinedStr: compile_joinedstr,
    FormattedValue: compile_formattedvalue,
    Lambda: compile_lambda,
    ListComp: compile_listcomp,
    SetComp: compile_setcomp,
    DictComp: compile_dictcomp,
    GeneratorExp: compile_genexp,
    Starred: compile_starred,
    Yield: compile_yield,
    YieldFrom: compile_yield,
    Await: compile_await,
    TypeAlias: compile_type_alias,
}
"""The compile function for each kind of expression."""


STMT_COMPILERS: dict[type[Statement], Callable[[Compiler, Any], StmtFn]] = {
    ExprStmt: compile_expr_stmt,
    Assign: compile_assign,
    AugAssign: compile_augassign,
    AnnAssign: compile_annassign,
    Delete: compile_delete,
    Pass: compile_pass,
    Break: compile_break,
    Continue: compile_continue,
    Return: compile_return,
    Raise: compile_raise,
    Global: compile_pass,
    Nonlocal: compile_pass,
    Assert: compile_assert,
    Import: compile_import,
    ImportFrom: compile_importfrom,
    If: compile_if,
    While: compile_while,
    For: compile_for,
    Try: compile_try,
    With: compile_with,
    FunctionDef: compile_funcdef,
    ClassDef: compile_classdef,
    Match: compile_match,
}
"""The compile function for each kind of statement."""
