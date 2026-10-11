"""close() and throw() across generators of different shapes: with and
without try/finally/with statements, delegating with yield from to each
other, and coroutines driven by hand.  Each check reports its own outcome."""
import contextlib


class AppError(Exception):
    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


def report(label, fn):
    try:
        print(label, 'ok', fn())
    except BaseException as e:
        print(label, type(e).__name__, e)


def plain_sub(log):
    # nothing here can stop GeneratorExit
    for i in range(3):
        try:
            yield i
        except ValueError:
            log.append('sub ValueError')
        finally:
            log.append('sub finally %d' % i)


def handling_sub(log):
    try:
        yield 'h'
    except GeneratorExit:
        log.append('sub handled exit')
    return 'sub rv'


def close_plain_delegator_of_handling_sub():
    log = []

    def outer():
        r = yield from handling_sub(log)
        log.append('outer resumed %s' % r)
    g = outer()
    next(g)
    log.append(g.close())
    return log


def close_handling_delegator_of_plain_sub():
    log = []

    def outer():
        try:
            yield from plain_sub(log)
        except GeneratorExit:
            log.append('outer got exit')
        log.append('outer after')
        return 'outer rv'
    g = outer()
    next(g)
    log.append(g.close())
    return log


def throw_into_plain_delegator():
    log = []

    def catcher():
        try:
            yield 'ready'
        except AppError as e:
            log.append('caught %s %d' % (e, e.code))
            yield 'recovered'

    def outer():
        yield from catcher()
    g = outer()
    next(g)
    log.append(g.throw(AppError('deep', 7)))
    return log


def throw_value_error_into_plain():
    log = []
    g = plain_sub(log)
    next(g)
    log.append(g.throw(ValueError))
    g.close()
    return log


def stop_iteration_in_plain():
    def g():
        try:
            yield next(iter([]))
        except StopIteration:
            yield 'caught'
    return list(g())


def finally_return_swallows():
    def g():
        try:
            yield 1
        finally:
            return 'from finally'
    gen = g()
    next(gen)
    return gen.close()


def with_suppress_exit():
    log = []

    def g():
        with contextlib.suppress(GeneratorExit):
            yield 1
        log.append('after with')
        return 'done'
    gen = g()
    next(gen)
    log.append(gen.close())
    return log


def coroutine_throw_user_exception():
    async def waiter():
        try:
            await Pause()
        except AppError as e:
            return 'coroutine caught %s' % e

    class Pause:
        def __await__(self):
            yield 'paused'

    c = waiter()
    first = c.send(None)
    try:
        c.throw(AppError('into coroutine'))
    except StopIteration as e:
        return first, e.value


def coroutine_close_runs_finally():
    log = []

    class Pause:
        def __await__(self):
            yield 'paused'

    async def worker():
        try:
            await Pause()
        finally:
            log.append('coroutine finally')
    c = worker()
    c.send(None)
    c.close()
    return log


report('close plain delegator, sub handles:', close_plain_delegator_of_handling_sub)
report('close handling delegator, plain sub:', close_handling_delegator_of_plain_sub)
report('throw user exception through yield from:', throw_into_plain_delegator)
report('throw ValueError into plain generator:', throw_value_error_into_plain)
report('StopIteration in a plain generator:', stop_iteration_in_plain)
report('finally return swallows close:', finally_return_swallows)
report('with suppressing GeneratorExit:', with_suppress_exit)
report('coroutine throw user exception:', coroutine_throw_user_exception)
report('coroutine close runs finally:', coroutine_close_runs_finally)
