"""contextlib.contextmanager and friends driving interpreted generators."""
import contextlib


@contextlib.contextmanager
def tag(name, log):
    log.append('<%s>' % name)
    try:
        yield name.upper()
    finally:
        log.append('</%s>' % name)


log = []
with tag('a', log) as a:
    log.append('inside ' + a)
    with tag('b', log):
        log.append('nested')
print(log)

# exception propagates into the generator; it can observe and re-raise
@contextlib.contextmanager
def observer(log):
    try:
        yield
    except ValueError as e:
        log.append('observed %s' % e)
        raise


log = []
try:
    with observer(log):
        raise ValueError('vv')
except ValueError as e:
    log.append('outer got %s' % e)
print(log)

# suppressing an exception by not re-raising
@contextlib.contextmanager
def swallow(*types):
    try:
        yield
    except types as e:
        print('  swallowed', type(e).__name__, e)


with swallow(KeyError, IndexError):
    {}['missing']
with swallow(KeyError):
    pass
print('after swallow')
try:
    with swallow(KeyError):
        raise TypeError('not swallowed')
except TypeError as e:
    print('TypeError escaped:', e)

# generator that does not yield -> RuntimeError
@contextlib.contextmanager
def no_yield():
    if False:
        yield


try:
    with no_yield():
        pass
except RuntimeError as e:
    print('RuntimeError', e)

# generator that yields twice -> RuntimeError
@contextlib.contextmanager
def yields_twice():
    yield 1
    yield 2


try:
    with yields_twice():
        pass
except RuntimeError as e:
    print('RuntimeError', e)

# converting an exception into another
@contextlib.contextmanager
def converting():
    try:
        yield
    except ZeroDivisionError as e:
        raise ArithmeticError('converted') from e


try:
    with converting():
        1 / 0
except ArithmeticError as e:
    print(type(e).__name__, e, '| cause', type(e.__cause__).__name__)

# used as a decorator
@tag('deco', log := [])
def decorated(x):
    log.append('call %d' % x)
    return x * 2


print(decorated(1), decorated(2), log)

# ExitStack with interpreted context managers and callbacks
log = []
with contextlib.ExitStack() as stack:
    for n in ('x', 'y'):
        stack.enter_context(tag(n, log))
    stack.callback(log.append, 'callback')
    log.append('body')
print(log)

# closing() calls close() on a generator
def counting():
    try:
        for i in range(10):
            yield i
    finally:
        print('  counting closed')


with contextlib.closing(counting()) as gen:
    for v in gen:
        if v == 2:
            break
print('after closing')

# suppress() and nullcontext with yields inside a generator
def gen_with_suppress():
    with contextlib.suppress(ZeroDivisionError):
        yield 'before div'
        1 / 0
        yield 'skipped'
    with contextlib.nullcontext('nc') as v:
        yield v


print(list(gen_with_suppress()))

# contextmanager whose generator handles the exception after cleanup
@contextlib.contextmanager
def transaction(log):
    log.append('begin')
    try:
        yield log
    except Exception as e:
        log.append('rollback %s' % type(e).__name__)
    else:
        log.append('commit')


log = []
with transaction(log):
    log.append('work 1')
with transaction(log):
    raise LookupError
print(log)

# a contextmanager-based helper used inside a generator, closed early
@contextlib.contextmanager
def opened(name):
    print('  open', name)
    yield name
    print('  close', name)


def reader():
    with opened('f1') as f:
        yield f + ':line1'
        yield f + ':line2'


r = reader()
print(next(r))
r.close()
print('reader closed')
