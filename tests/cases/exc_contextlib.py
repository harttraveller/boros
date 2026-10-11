# contextlib with interpreted generators, interpreted exception classes and callbacks.
# Each section runs independently so that one failure does not hide the others.
import contextlib
import io


class AppError(Exception):
    pass


class SubError(AppError):
    pass


log = []


def section(f):
    log.clear()
    try:
        f()
    except Exception as e:
        print('SECTION %s FAILED: %s: %s' % (f.__name__, type(e).__name__, e))
    else:
        print(f.__name__, log)
    return f


@contextlib.contextmanager
def tag(name):
    log.append('<%s>' % name)
    try:
        yield name
    finally:
        log.append('</%s>' % name)


@contextlib.contextmanager
def catching(*types):
    try:
        yield
    except types as e:
        log.append('caught %s %s' % (type(e).__name__, e.args))


@contextlib.contextmanager
def converting():
    try:
        yield
    except KeyError as k:
        raise AppError('converted') from k


@section
def nested_tags():
    with tag('a') as t:
        with tag('b'):
            log.append('body ' + t)


@section
def host_exception_through_generator():
    try:
        with tag('x'):
            raise ValueError('host through')
    except ValueError as e:
        log.append('outside %s %s' % (type(e).__name__, e))


@section
def interp_exception_through_generator():
    try:
        with tag('x'):
            raise AppError('through')
    except AppError as e:
        log.append('outside %s %s' % (type(e).__name__, e))


@section
def generator_catches_host():
    with catching(ValueError):
        int('nope')


@section
def generator_catches_interp():
    with catching(AppError):
        raise SubError('sub')


@section
def generator_does_not_catch():
    try:
        with catching(KeyError):
            raise AppError('not caught')
    except AppError as e:
        log.append('propagated: %s %s' % (type(e).__name__, e))


@section
def generator_converts():
    try:
        with converting():
            {}['k']
    except AppError as e:
        log.append('converted: %s %s' % (e, type(e.__cause__).__name__))


@section
def suppress_host():
    with contextlib.suppress(ZeroDivisionError):
        1 / 0
    log.append('after')


@section
def suppress_interp():
    with contextlib.suppress(AppError):
        raise SubError('suppressed sub')
    log.append('after')


@section
def suppress_not_matching():
    try:
        with contextlib.suppress(SubError):
            raise AppError('base not suppressed')
    except AppError as e:
        log.append('not suppressed: %s' % e)


@contextlib.contextmanager
def no_yield():
    if False:
        yield


@contextlib.contextmanager
def twice():
    yield 1
    yield 2


@section
def bad_generators():
    try:
        with no_yield():
            pass
    except RuntimeError as e:
        log.append('RuntimeError: %s' % e)
    try:
        with twice():
            pass
    except RuntimeError as e:
        log.append('RuntimeError: %s' % e)


@contextlib.contextmanager
def reraising():
    try:
        yield
    except AppError:
        log.append('saw and re-raised')
        raise


@section
def generator_reraises():
    try:
        with reraising():
            raise AppError('again')
    except AppError as e:
        log.append('re-raised: %s' % e)


class Res:
    def __init__(self, name, suppress=False):
        self.name = name
        self.suppress = suppress

    def __enter__(self):
        log.append('open ' + self.name)
        return self

    def __exit__(self, et, ev, tb):
        log.append('close %s %s %s' % (self.name, et.__name__ if et else None, type(ev).__name__))
        return self.suppress


@section
def exitstack_normal():
    with contextlib.ExitStack() as stack:
        for n in ('r1', 'r2', 'r3'):
            stack.enter_context(Res(n))
        stack.callback(log.append, 'callback')


@section
def exitstack_host_error():
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(Res('s1'))
            stack.enter_context(Res('s2'))
            raise ValueError('in stack')
    except ValueError as e:
        log.append('stack propagated %s' % e)


@section
def exitstack_interp_error():
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(Res('s1'))
            raise SubError('interp in stack')
    except AppError as e:
        log.append('stack propagated %s %s' % (type(e).__name__, e))


@section
def exitstack_suppress():
    with contextlib.ExitStack() as stack:
        stack.enter_context(Res('outer'))
        stack.enter_context(Res('suppressor', suppress=True))
        raise AppError('stack suppressed')


def exit_cb(et, ev, tb):
    log.append('push %s %s %s' % (et.__name__, type(ev).__name__, ev.args))
    return False


@section
def exitstack_push():
    try:
        with contextlib.ExitStack() as stack:
            stack.push(exit_cb)
            raise SubError('pushed')
    except AppError as e:
        log.append('push propagated %s' % type(e).__name__)


@section
def exitstack_pop_all():
    with contextlib.ExitStack() as stack:
        stack.enter_context(Res('p'))
        moved = stack.pop_all()
    log.append('after pop_all')
    moved.close()


@section
def exitstack_callback_raises():
    def bad():
        raise AppError('callback failed')
    try:
        with contextlib.ExitStack() as stack:
            stack.callback(bad)
            stack.enter_context(Res('c'))
    except AppError as e:
        log.append('callback error %s' % e)


class Closable:
    def close(self):
        log.append('closed')


@section
def misc_helpers():
    with contextlib.closing(Closable()):
        pass
    with contextlib.nullcontext(5) as five:
        log.append(five)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print('captured')
    log.append(buf.getvalue())


@tag('deco')
def decorated():
    log.append('inside decorated')


@section
def contextmanager_as_decorator():
    decorated()
