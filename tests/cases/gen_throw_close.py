"""throw() and close(): GeneratorExit, finally blocks, return values."""


def worker(name):
    print('  %s start' % name)
    try:
        while True:
            try:
                x = yield
                print('  %s got %r' % (name, x))
            except ValueError as e:
                print('  %s handled ValueError(%s)' % (name, e))
                yield 'recovered'
    finally:
        print('  %s finally' % name)


g = worker('w')
next(g)
g.send(1)
print('throw returns', g.throw(ValueError('bad')))
print('next after recover', next(g))
g.send(2)
# an exception not handled by the generator propagates out of throw()
try:
    g.throw(KeyError('k'))
except KeyError as e:
    print('propagated KeyError', e)
# the generator is now finished
print(next(g, 'finished'))

# throw with an exception class (instantiated automatically)
def catcher():
    try:
        yield 1
    except Exception as e:
        yield 'caught %s %r' % (type(e).__name__, e.args)


g = catcher()
next(g)
print(g.throw(IndexError))
g = catcher()
next(g)
print(g.throw(TypeError('t', 2)))

# throw into a not-yet-started generator: raised at the start, finally does not run
def unstarted():
    try:
        yield 1
    finally:
        print('  never printed')


g = unstarted()
try:
    g.throw(RuntimeError('early'))
except RuntimeError as e:
    print('early throw', e)
print(next(g, 'closed'))

# throw that makes the generator return -> StopIteration with the value
def returner():
    try:
        yield 1
    except ValueError:
        return 'ret-from-throw'


g = returner()
next(g)
try:
    g.throw(ValueError)
except StopIteration as e:
    print('StopIteration', e.value)

# close(): GeneratorExit raised at the yield, finally runs
def closable():
    try:
        yield 1
        yield 2
    except GeneratorExit:
        print('  saw GeneratorExit')
        raise
    finally:
        print('  closable finally')


g = closable()
next(g)
print('close ->', g.close())
print('close again ->', g.close())
print(next(g, 'after close'))

# close() on an unstarted generator: nothing runs
g = closable()
print('close unstarted ->', g.close())

# close() on a finished generator
g = closable()
list(g)
print('close finished ->', g.close())

# GeneratorExit is not an Exception
def broad():
    try:
        yield 1
    except Exception:
        print('  should not catch GeneratorExit')
    finally:
        print('  broad finally')


g = broad()
next(g)
g.close()
print(issubclass(GeneratorExit, Exception), issubclass(GeneratorExit, BaseException))

# finally runs when a generator is dropped (refcount reaches zero)
def dropped():
    try:
        yield 1
    finally:
        print('  dropped finally')


g = dropped()
next(g)
print('dropping')
del g
print('dropped')

# nested try/finally, order of cleanups when closed
def nested():
    try:
        try:
            yield 'inner'
        finally:
            print('  inner cleanup')
    finally:
        print('  outer cleanup')


g = nested()
next(g)
g.close()

# a finally that yields during normal iteration is fine
def finally_yields():
    try:
        yield 'body'
    finally:
        yield 'from finally'


print(list(finally_yields()))

# raising another exception during close propagates it
def raises_in_close():
    try:
        yield
    finally:
        raise KeyError('during close')


g = raises_in_close()
next(g)
try:
    g.close()
except KeyError as e:
    print('KeyError', e, type(e.__context__).__name__)

# throw() an exception the generator converts into another
def converter():
    try:
        yield
    except ZeroDivisionError as e:
        raise ValueError('converted') from e


g = converter()
next(g)
try:
    g.throw(ZeroDivisionError('zd'))
except ValueError as e:
    print('ValueError', e, 'cause:', repr(e.__cause__))

# exception context is preserved across a yield inside an except block
import sys


def ctx():
    try:
        raise KeyError('orig')
    except KeyError:
        yield sys.exc_info()[0].__name__
        yield sys.exc_info()[0].__name__
    yield sys.exc_info()[0]


g = ctx()
print(next(g))
try:
    raise ValueError('outside')
except ValueError:
    print(next(g))
print(next(g))

# bare raise after a yield re-raises the handled exception
def reraiser():
    try:
        raise IndexError('ix')
    except IndexError:
        yield 'in handler'
        raise


g = reraiser()
print(next(g))
try:
    next(g)
except IndexError as e:
    print('reraised', e)

# gi_running / "generator already executing"
def self_ref():
    yield gen_ref.gi_running
    next(gen_ref)


gen_ref = self_ref()
print('running inside:', next(gen_ref), 'outside:', gen_ref.gi_running)
try:
    next(gen_ref)
except ValueError as e:
    print('ValueError', e)
