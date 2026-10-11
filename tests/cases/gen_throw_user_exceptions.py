"""Exceptions of *user-defined* classes thrown into generators: throw()
with an instance or a class, through yield from, and via
contextlib.contextmanager / ExitStack (which call throw() / __exit__
from host code).  Each check reports its own outcome."""
import contextlib


class AppError(Exception):
    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


class Retry(AppError):
    pass


def report(label, fn):
    try:
        print(label, 'ok', fn())
    except BaseException as e:
        print(label, type(e).__name__, e)


def catcher():
    try:
        yield 'ready'
    except AppError as e:
        yield 'caught %s %s code=%d' % (type(e).__name__, e, e.code)


def throw_instance():
    g = catcher()
    next(g)
    return g.throw(Retry('again', code=5))


def throw_class():
    g = catcher()
    next(g)
    return g.throw(AppError)


report('throw instance:', throw_instance)

def throw_class_no_args():
    class Bare(Exception):
        pass

    def gen():
        try:
            yield
        except Bare as e:
            yield 'caught Bare %r' % (e.args,)
    g = gen()
    next(g)
    return g.throw(Bare)


report('throw class:', throw_class_no_args)

def throw_uncaught():
    def gen():
        yield 1
    g = gen()
    next(g)
    try:
        g.throw(AppError('not handled', code=9))
    except AppError as e:
        return 'propagated %s code=%d' % (e, e.code)


report('throw uncaught:', throw_uncaught)

def throw_delegated():
    def outer():
        yield from catcher()
    g = outer()
    next(g)
    return g.throw(AppError('to the subgenerator', code=3))


report('throw through yield from:', throw_delegated)

# contextlib.contextmanager: the exception from the with body is thrown
# into the interpreted generator by contextlib (host code)
@contextlib.contextmanager
def observe(log):
    try:
        yield
    except AppError as e:
        log.append('observed %s code=%d' % (e, e.code))
        raise


def cm_observe_reraise():
    log = []
    try:
        with observe(log):
            raise AppError('in body', code=4)
    except AppError as e:
        log.append('outer got %s' % type(e).__name__)
    return log


report('contextmanager re-raise:', cm_observe_reraise)

@contextlib.contextmanager
def swallow():
    try:
        yield
    except AppError as e:
        print('  swallowed', type(e).__name__, e)


def cm_swallow():
    with swallow():
        raise Retry('swallow me')
    return 'continued'


report('contextmanager suppress:', cm_swallow)

@contextlib.contextmanager
def convert():
    try:
        yield
    except KeyError as e:
        raise AppError('converted from KeyError', code=2) from e


def cm_convert():
    try:
        with convert():
            {}['k']
    except AppError as e:
        return 'got %s code=%d cause=%s' % (e, e.code, type(e.__cause__).__name__)


report('contextmanager convert:', cm_convert)

# ExitStack calls the interpreted __exit__ from host code
class Recorder:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, typ, val, tb):
        self.log.append('exit got %s / %s code=%s' % (typ.__name__, type(val).__name__, getattr(val, 'code', '?')))
        return True


def exitstack_user_exc():
    log = []
    with contextlib.ExitStack() as stack:
        stack.enter_context(Recorder(log))
        raise AppError('inside stack', code=8)
    return log


report('ExitStack interpreted __exit__:', exitstack_user_exc)

# contextlib.suppress and contextlib.closing with user exceptions
def suppress_user():
    with contextlib.suppress(AppError):
        raise Retry('suppressed by base class')
    return 'suppressed'


report('suppress user exception:', suppress_user)
