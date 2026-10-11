# generator.close() semantics when the interpreted generator handles GeneratorExit.
# (GeneratorExit must behave like any other exception thrown in at the yield.)


def section(f):
    try:
        r = f()
    except BaseException as e:
        print('SECTION %s FAILED: %s: %s' % (f.__name__, type(e).__name__, e))
    else:
        print(f.__name__, r)
    return f


@section
def close_plain():
    log = []

    def g():
        try:
            yield 1
        finally:
            log.append('finally')
    gen = g()
    next(gen)
    return gen.close(), log


@section
def handled_then_continues():
    log = []

    def g():
        try:
            yield 1
        except GeneratorExit:
            log.append('cleanup')
        log.append('after try')
    gen = g()
    next(gen)
    gen.close()
    return log


@section
def close_returns_value():
    # Python 3.13: close() returns the generator's return value
    def g():
        try:
            yield 1
        except GeneratorExit:
            return 'rv'
    gen = g()
    next(gen)
    return gen.close()


@section
def finally_return_swallows_exit():
    def g():
        try:
            yield 1
        finally:
            return 'from finally'
    gen = g()
    next(gen)
    return gen.close()


@section
def handled_in_loop_then_yield():
    state = []

    def g():
        for i in range(3):
            try:
                yield i
            except GeneratorExit:
                state.append('exit %d' % i)
                if len(state) > 1:
                    return
        # never reached
    gen = g()
    next(gen)
    try:
        gen.close()
    except RuntimeError as e:
        state.append('RuntimeError: %s' % e)
    gen.close()
    return state


@section
def handler_raises_other():
    def g():
        try:
            yield 1
        except GeneratorExit:
            raise ValueError('replaced exit')
    gen = g()
    next(gen)
    try:
        gen.close()
    except ValueError as e:
        return 'ValueError: %s ctx=%s' % (e, type(e.__context__).__name__)


@section
def with_suppresses_exit():
    log = []

    class Swallow:
        def __enter__(self):
            return self

        def __exit__(self, et, ev, tb):
            log.append('exit got %s' % et.__name__)
            return True

    def g():
        with Swallow():
            yield 1
        log.append('after with')
    gen = g()
    next(gen)
    gen.close()
    return log


@section
def throw_generator_exit_explicitly():
    log = []

    def g():
        try:
            yield 1
        except GeneratorExit:
            log.append('caught')
        log.append('continued')
        yield 2
    gen = g()
    next(gen)
    log.append(gen.throw(GeneratorExit))
    return log


@section
def close_delegating_generator():
    # close() of a generator suspended in `yield from sub()`: sub is closed
    # first, then GeneratorExit is raised in the delegating generator
    log = []

    def sub():
        try:
            yield 1
        except GeneratorExit:
            log.append('sub cleanup')
        return 'subval'

    def outer():
        try:
            v = yield from sub()
            log.append('outer continued with %s' % v)
            yield 2
        except GeneratorExit:
            log.append('outer got GeneratorExit')
            raise
    g = outer()
    next(g)
    log.append(g.close())
    return log


@section
def close_delegating_outer_handles():
    log = []

    def sub():
        try:
            yield 1
        finally:
            log.append('sub finally')

    def outer():
        try:
            yield from sub()
        except GeneratorExit:
            log.append('outer handled')
        return 'outer rv'
    g = outer()
    next(g)
    log.append(g.close())
    return log


@section
def close_while_iterating_other_generator():
    log = []

    def helper():
        yield 'h1'
        yield 'h2'
        return 'helper done'

    def g():
        try:
            yield 1
        except GeneratorExit:
            log.append(list(helper()))
            log.append('handler finished')
        log.append('after try')
    gen = g()
    next(gen)
    log.append(gen.close())
    return log


@section
def contextmanager_swallows_exit_then_yield_from():
    import contextlib
    log = []

    @contextlib.contextmanager
    def swallow_exit():
        try:
            yield
        except GeneratorExit:
            log.append('cm swallowed')

    def empty():
        return 'e'
        yield

    def g():
        with swallow_exit():
            yield 1
        r = yield from empty()
        log.append('after yield from %s' % r)
    gen = g()
    next(gen)
    log.append(gen.close())
    return log
