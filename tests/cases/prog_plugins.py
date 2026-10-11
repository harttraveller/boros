"""Decorator-heavy plugin registry: parameterized decorators, functools.wraps,
class decorators, __init_subclass__ auto-registration with keyword args,
descriptors for typed config options, a hook system with priorities,
context-managed plugin activation, and plugins defined in a helper module."""
import functools
import contextlib
import sys
import _prog_plugins_extra as extra

REGISTRY = {}
HOOKS = {}
CALLS = []


class PluginError(Exception):
    pass


def hook(event, priority=0):
    def deco(fn):
        HOOKS.setdefault(event, []).append((priority, fn.__qualname__, fn))
        return fn
    return deco


def trace(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        CALLS.append(fn.__name__)
        return fn(*args, **kwargs)
    return wrapper


def retry(times, exceptions=(Exception,)):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            last = None
            for attempt in range(1, times + 1):
                try:
                    return fn(*a, attempt=attempt, **kw)
                except exceptions as e:
                    last = e
            raise PluginError("%s failed after %d attempts" % (fn.__name__, times)) from last
        return wrapper
    return deco


class Option:
    """A typed config option descriptor."""

    def __init__(self, type_, default):
        self.type = type_
        self.default = default

    def __set_name__(self, owner, name):
        self.name = name
        owner.options = getattr(owner, "options", ()) + (name,)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj, value):
        if not isinstance(value, self.type):
            raise TypeError("%s.%s must be %s, not %s" % (type(obj).__name__, self.name, self.type.__name__,
                                                          type(value).__name__))
        obj.__dict__[self.name] = value


class Plugin:
    name = None
    enabled = Option(bool, True)
    level = Option(int, 1)

    def __init_subclass__(cls, /, name=None, abstract=False, **kw):
        super().__init_subclass__(**kw)
        if abstract:
            return
        cls.name = name or cls.__name__.lower()
        if cls.name in REGISTRY:
            raise PluginError("duplicate plugin %r" % cls.name)
        REGISTRY[cls.name] = cls

    def __init__(self, **config):
        for k, v in config.items():
            if k not in type(self).options:
                raise PluginError("%s: unknown option %r" % (self.name, k))
            setattr(self, k, v)

    def run(self, text):
        raise NotImplementedError

    def __repr__(self):
        opts = ", ".join("%s=%r" % (o, getattr(self, o)) for o in type(self).options)
        return "<%s %s>" % (self.name, opts)


def singleton(cls):
    instances = {}

    @functools.wraps(cls, updated=())
    def get(*a, **kw):
        if cls not in instances:
            instances[cls] = cls(*a, **kw)
        return instances[cls]
    get.cls = cls
    return get


class TextPlugin(Plugin, abstract=True):
    def run(self, text):
        return self.transform(text) if self.enabled else text


class Upper(TextPlugin):
    @trace
    def transform(self, text):
        return text.upper()


class Reverse(TextPlugin, name="rev"):
    width = Option(int, 0)

    @trace
    def transform(self, text):
        return text[::-1].rjust(self.width)


class Repeat(TextPlugin, name="repeat"):
    @trace
    def transform(self, text):
        return " ".join([text] * self.level)


@singleton
class Counter(Plugin, name="counter"):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.seen = 0

    def run(self, text):
        self.seen += len(text)
        return text


class Flaky(Plugin, name="flaky"):
    @retry(3, (ConnectionError,))
    def run(self, text, attempt=1):
        if attempt < 3:
            raise ConnectionError("attempt %d" % attempt)
        return text + "!"


class AlwaysBroken(Plugin, name="broken"):
    @retry(2, (ConnectionError,))
    def run(self, text, attempt=1):
        raise ConnectionError("down (attempt %d)" % attempt)


@hook("start", priority=10)
def announce(ctx):
    ctx.append("announce")


@hook("start")
def setup(ctx):
    ctx.append("setup")


@hook("start", priority=5)
@trace
def warmup(ctx):
    ctx.append("warmup")


def fire(event, ctx):
    for prio, qn, fn in sorted(HOOKS.get(event, ()), key=lambda t: (-t[0], t[1])):
        fn(ctx)
    return ctx


@contextlib.contextmanager
def activated(*names, **config):
    plugins = [REGISTRY[n](**config.get(n, {})) for n in names]
    CALLS.append("enter:" + ",".join(names))
    try:
        yield plugins
    except PluginError as e:
        CALLS.append("error:%s" % e)
        raise
    finally:
        CALLS.append("exit")


def pipeline(text, plugins):
    for p in plugins:
        text = p.run(text)
    return text


extra.register(REGISTRY, Plugin)
print(sorted(REGISTRY), fire("start", []))
with activated("upper", "rev", "repeat", config=None) if False else activated(
        "upper", "rev", "repeat", rev={"width": 12}, repeat={"level": 2}) as ps:
    print(ps, pipeline("hello", ps))
    ps[0].enabled = False
    print(pipeline("hello", ps))
print(CALLS)
print(Upper.transform.__name__, Upper.transform.__wrapped__.__qualname__, warmup.__name__, Upper.options,
      Reverse.options, type(Reverse.__dict__["width"]).__name__, Reverse.width.default)
c1, c2 = Counter(), Counter()
c1.run("abc")
print(c1 is c2, c2.seen, Counter.__name__, Counter.cls.name, REGISTRY["counter"] is Counter.cls)
print(Flaky().run("ok"), pipeline("x", [REGISTRY["shout"](), REGISTRY["rev"](width=4)]))
for bad in (lambda: AlwaysBroken().run("x"), lambda: Upper(level="high"), lambda: Upper(colour=1),
            lambda: type("Upper2", (TextPlugin,), {}, name="upper"), lambda: Plugin().run("x")):
    try:
        bad()
    except (PluginError, TypeError, NotImplementedError) as e:
        cause = e.__cause__
        print(type(e).__name__, "|", e, "|", repr(cause) if cause else "-")
print(extra.__name__, extra.describe(REGISTRY["shout"]))


def check(label, f):
    try:
        print(label, f())
    except Exception as e:
        print(label, "raised", type(e).__name__, e)


check("helper module in sys.modules:", lambda: sys.modules[extra.__name__] is extra)
check("main module in sys.modules:", lambda: getattr(sys.modules[__name__], "REGISTRY", None) is REGISTRY)
try:
    with activated("upper") as ps:
        raise PluginError("inside")
except PluginError as e:
    print("propagated:", e, CALLS[-2:])
