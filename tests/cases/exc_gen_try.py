# try/except/else/finally and with statements inside generator functions
# (the generator-mode compilation of these statements).


class E(Exception):
    pass


def section(f):
    try:
        r = f()
    except BaseException as e:
        print('SECTION %s FAILED: %s: %s' % (f.__name__, type(e).__name__, e))
    else:
        print(f.__name__, r)
    return f


@section
def order():
    log = []

    def g(fail):
        try:
            log.append('body')
            yield 1
            if fail:
                raise E('x')
            yield 2
        except E as e:
            log.append('except %s' % e)
            yield 'h'
        else:
            log.append('else')
            yield 'e'
        finally:
            log.append('finally')
            yield 'f'
        log.append('after')
    return list(g(False)), list(g(True)), log


@section
def finally_overrides_return():
    def g():
        try:
            yield 1
            return 'try'
        finally:
            return 'finally'
    gen = g()
    next(gen)
    try:
        next(gen)
    except StopIteration as s:
        return s.value


@section
def finally_swallows_exception():
    def g():
        try:
            yield 1
            raise E('lost')
        finally:
            return 'swallowed'
    gen = g()
    next(gen)
    try:
        next(gen)
    except StopIteration as s:
        return s.value


@section
def break_continue_in_finally():
    def g():
        for i in range(4):
            try:
                yield i
                if i == 1:
                    raise E('skip')
            finally:
                if i == 1:
                    continue
                if i == 2:
                    break
        yield 'end'
    return list(g())


@section
def name_unbound_after_handler():
    def g():
        try:
            yield 1
            raise E('bound')
        except E as err:
            yield str(err)
        try:
            yield err
        except NameError as ne:
            yield 'NameError: %s' % ne
        except UnboundLocalError as ue:
            yield 'UnboundLocalError: %s' % ue
    return list(g())


@section
def handler_types_checked():
    def g():
        try:
            yield 1
            raise E('a')
        except 42:
            yield 'no'
    try:
        return list(g())
    except TypeError as t:
        return 'TypeError: %s' % t


@section
def chaining_in_generator():
    def g():
        try:
            yield 1
            raise KeyError('k')
        except KeyError as k:
            yield 2
            raise E('wrapped') from k
    out = []
    try:
        for x in g():
            out.append(x)
    except E as e:
        out.append((type(e.__cause__).__name__, e.__context__ is e.__cause__))
    return out


@section
def bare_raise_after_yield_in_handler():
    def g():
        try:
            raise E('kept across yield')
        except E:
            yield 'in handler'
            raise
    gen = g()
    out = [next(gen)]
    try:
        next(gen)
    except E as e:
        out.append(str(e))
    return out


class CM:
    def __init__(self, log, suppress=False):
        self.log = log
        self.suppress = suppress

    def __enter__(self):
        self.log.append('enter')
        return self

    def __exit__(self, et, ev, tb):
        self.log.append('exit %s %s' % (et.__name__ if et else None, type(ev).__name__))
        return self.suppress


@section
def with_in_generator():
    log = []

    def g():
        with CM(log):
            yield 1
            yield 2
        with CM(log, suppress=True):
            yield 3
            raise E('suppressed in gen')
        yield 4
    return list(g()), log


@section
def with_exception_propagates_from_generator():
    log = []

    def g():
        with CM(log):
            yield 1
            raise E('through with')
    try:
        list(g())
    except E as e:
        log.append('outside %s' % e)
    return log


@section
def with_host_cm_in_generator():
    import contextlib
    log = []

    def g():
        with contextlib.suppress(E):
            yield 1
            raise E('host suppress in gen')
        yield 2
    return list(g()), log


@section
def throw_while_in_with():
    log = []

    def g():
        with CM(log):
            yield 1
    gen = g()
    next(gen)
    try:
        gen.throw(ValueError('thrown into with'))
    except ValueError as v:
        log.append('propagated %s' % v)
    return log
