# Exceptions crossing generator boundaries: throw(), close(), finally in generators,
# StopIteration -> RuntimeError, exceptions propagating out of yield from.


class GenError(Exception):
    pass


def section(f):
    try:
        r = f()
    except Exception as e:
        print('SECTION %s FAILED: %s: %s' % (f.__name__, type(e).__name__, e))
    else:
        print(f.__name__, r)
    return f


def counter(log):
    try:
        for i in range(3):
            try:
                yield i
            except GenError as e:
                log.append('gen caught %s' % e)
                yield 'recovered'
    finally:
        log.append('gen finally')


@section
def raise_out_of_generator():
    def g():
        yield 1
        raise GenError('from gen')
    out = []
    try:
        for x in g():
            out.append(x)
    except GenError as e:
        out.append('caught %s %s' % (type(e).__name__, e))
    return out


@section
def throw_interp_exception():
    log = []
    gen = counter(log)
    log.append(next(gen))
    log.append(gen.throw(GenError('thrown')))
    log.append(next(gen))
    gen.close()
    return log


@section
def throw_instance_type_seen_inside():
    seen = []

    def g():
        try:
            yield
        except Exception as e:
            seen.append((type(e).__name__, isinstance(e, GenError), e.args))
            yield 'handled'
    gen = g()
    next(gen)
    r = gen.throw(GenError('t', 2))
    return seen, r


@section
def throw_class():
    def g():
        try:
            yield 1
        except KeyError as e:
            yield 'key %r' % (e.args,)
    gen = g()
    next(gen)
    return gen.throw(KeyError)


@section
def throw_uncaught_propagates():
    def g():
        yield 1
        yield 2
    gen = g()
    next(gen)
    try:
        gen.throw(GenError('not handled'))
    except GenError as e:
        res = 'propagated %s' % e
    try:
        next(gen)
    except StopIteration:
        res += ' / exhausted'
    return res


@section
def close_runs_finally():
    log = []
    gen = counter(log)
    next(gen)
    gen.close()
    gen.close()
    return log


@section
def generator_exit_caught():
    log = []

    def g():
        try:
            yield 1
        except GeneratorExit:
            log.append('GeneratorExit seen')
            raise
    gen = g()
    next(gen)
    gen.close()
    return log


@section
def stopiteration_inside_generator():
    def g():
        yield 1
        raise StopIteration('bad')
    try:
        list(g())
    except RuntimeError as e:
        return 'RuntimeError: %s; cause=%s' % (e, type(e.__cause__).__name__)


@section
def next_inside_generator_exhausts():
    def g():
        it = iter([])
        yield next(it)
    try:
        list(g())
    except RuntimeError as e:
        return 'RuntimeError: %s' % e


@section
def return_value():
    def g():
        yield 1
        return 'retval'
    gen = g()
    next(gen)
    try:
        next(gen)
    except StopIteration as e:
        return e.value, e.args


@section
def yield_from_propagates():
    def inner():
        yield 'i1'
        raise GenError('inner failed')

    def outer():
        try:
            yield from inner()
        except GenError as e:
            yield 'outer caught %s' % e
    return list(outer())


@section
def yield_from_throw_delegates():
    log = []

    def inner():
        try:
            yield 'inner'
        except GenError as e:
            log.append('inner got %s' % e)
            return 'inner done'

    def outer():
        r = yield from inner()
        log.append('outer got %s' % r)
        yield 'outer'
    gen = outer()
    next(gen)
    log.append(gen.throw(GenError('delegated')))
    return log


@section
def yield_from_return_value():
    def inner():
        yield 1
        return 'ret'

    def outer():
        r = yield from inner()
        yield r
    return list(outer())


@section
def yield_in_finally_and_except():
    def g():
        try:
            yield 'try'
            raise GenError('x')
        except GenError:
            yield 'except'
        finally:
            yield 'finally'
    return list(g())


@section
def exception_in_genexp():
    try:
        return sum(1 // x for x in [1, 2, 0])
    except ZeroDivisionError as e:
        return 'ZeroDivisionError: %s' % e


@section
def generator_running_error():
    def g():
        yield next(gen)
    gen = g()
    try:
        next(gen)
    except ValueError as e:
        return 'ValueError: %s' % e


@section
def send_to_new_generator():
    def g():
        yield 1
    try:
        g().send(5)
    except TypeError as e:
        return 'TypeError: %s' % e


@section
def handler_state_across_yield():
    import sys

    def g():
        try:
            raise GenError('active')
        except GenError:
            yield type(sys.exception()).__name__
            yield type(sys.exception()).__name__
    gen = g()
    first = next(gen)
    outside = sys.exception()
    second = next(gen)
    return first, outside, second


@section
def exception_context_in_generator():
    def g():
        try:
            yield
        except GenError:
            raise ValueError('during gen handling')
    gen = g()
    next(gen)
    try:
        gen.throw(GenError('ctx'))
    except ValueError as e:
        return type(e.__context__).__name__, e.__context__.args
