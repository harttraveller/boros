"""A command-line tool framework: subcommands are plain annotated functions
registered with a decorator; their signatures (inspect.signature) and type
annotations (typing.get_type_hints) drive an argparse parser and value
conversion. Exercises __annotations__ on functions/classes/modules,
inspect.Signature binding, argparse with exit_on_error=False, and error
reporting. Sections are independent."""
import argparse
import inspect
import typing

COMMANDS = {}
VERSION: str = "1.4"
DEBUG: bool


def section(name):
    def deco(fn):
        try:
            print(name + ":", fn())
        except Exception as e:
            print(name + ": raised", type(e).__name__, e)
        return fn
    return deco


def command(fn):
    COMMANDS[fn.__name__.replace("_", "-")] = fn
    return fn


@command
def add(a: int, b: int = 0, *, verbose: bool = False) -> int:
    """Add two integers."""
    r = a + b
    return "%d + %d = %d" % (a, b, r) if verbose else r


@command
def scale(values: list, factor: float = 2.0) -> list:
    """Scale every value by a factor."""
    return [round(float(v) * factor, 3) for v in values]


@command
def greet_user(name: str, times: int = 1, *, shout: bool = False):
    """Greet someone."""
    msg = ("hello %s" % name) * 1
    return [msg.upper() if shout else msg] * times


class Settings:
    retries: int = 3
    timeout: float
    name: str = "tool"


def build_parser():
    parser = argparse.ArgumentParser(prog="tool", exit_on_error=False)
    subs = parser.add_subparsers(dest="cmd")
    for name, fn in COMMANDS.items():
        p = subs.add_parser(name, help=inspect.getdoc(fn), exit_on_error=False)
        hints = typing.get_type_hints(fn)
        for param in inspect.signature(fn).parameters.values():
            typ = hints.get(param.name, str)
            if typ is list:
                p.add_argument(param.name, nargs="+")
            elif param.kind is param.KEYWORD_ONLY and typ is bool:
                p.add_argument("--" + param.name, action="store_true")
            elif param.default is param.empty:
                p.add_argument(param.name, type=typ)
            else:
                p.add_argument("--" + param.name, type=typ, default=param.default)
    return parser


def run(argv):
    parser = build_parser()
    ns = vars(parser.parse_args(argv))
    fn = COMMANDS[ns.pop("cmd")]
    sig = inspect.signature(fn)
    pos = [ns.pop(p.name) for p in sig.parameters.values() if p.default is p.empty and p.kind is not p.KEYWORD_ONLY]
    bound = sig.bind(*pos, **ns)
    return fn(*bound.args, **bound.kwargs)


@section("annotations")
def _():
    return add.__annotations__, Settings.__annotations__, __annotations__


@section("type hints")
def _():
    return typing.get_type_hints(greet_user), typing.get_type_hints(Settings)


@section("signatures")
def _():
    return [str(inspect.signature(f)) for f in COMMANDS.values()]


@section("bind")
def _():
    sig = inspect.signature(add)
    b = sig.bind(1, verbose=True)
    b.apply_defaults()
    return dict(b.arguments), b.args, b.kwargs


@section("bind error")
def _():
    return inspect.signature(add).bind(1, 2, 3)


@section("function __dict__")
def _():
    add.cli_hidden = False
    return sorted(vars(add)), sorted(add.__dict__)


@section("docs")
def _():
    return [(n, inspect.getdoc(f)) for n, f in COMMANDS.items()], add.__doc__


for argv in (["add", "2", "--b", "5"], ["add", "7", "--verbose"], ["scale", "1", "2.5", "--factor", "0.5"],
             ["greet-user", "ada", "--times", "2", "--shout"], ["add", "x"], ["nope"]):
    try:
        print(argv, "->", run(argv))
    except (argparse.ArgumentError, SystemExit, TypeError, KeyError) as e:
        print(argv, "->", type(e).__name__, e)
