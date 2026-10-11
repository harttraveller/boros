"""StopIteration inside generators (PEP 479): it can be caught by the
generator's own try/except even when the try block contains a yield;
only an uncaught StopIteration becomes RuntimeError."""
import contextlib


# the PEP 479 recommended pattern
def take(it, n):
    for _ in range(n):
        try:
            yield next(it)
        except StopIteration:
            return


print(list(take(iter([1, 2]), 5)))
print(list(take(iter('abcdef'), 3)))

# raise StopIteration explicitly in a try that also yields
def explicit():
    try:
        yield 1
        raise StopIteration('x')
    except StopIteration as e:
        yield 'caught %r' % (e,)


print(list(explicit()))

# caught by a broader handler
def broad():
    try:
        yield next(iter([]))
    except Exception as e:
        yield 'Exception handler got %s' % type(e).__name__


print(list(broad()))

# StopIteration thrown in with throw() can be caught too
def catch_thrown():
    try:
        yield 'ready'
    except StopIteration as e:
        yield 'thrown %r' % (e.args,)


g = catch_thrown()
next(g)
print(g.throw(StopIteration('via throw')))

# a StopIteration from a nested call in a with block inside a generator
def with_suppress():
    with contextlib.suppress(StopIteration):
        yield 'before'
        next(iter(()))
        yield 'not reached'
    yield 'after with'


print(list(with_suppress()))

# zip-like generator written with the PEP 479 idiom
def my_zip(*iterables):
    its = [iter(x) for x in iterables]
    while True:
        try:
            items = [next(it) for it in its]
        except StopIteration:
            return
        yield tuple(items)


print(list(my_zip('abc', [1, 2, 3, 4])))

def my_zip2(*iterables):
    its = [iter(x) for x in iterables]
    while its:
        try:
            yield tuple([next(it) for it in its])
        except StopIteration:
            return


print(list(my_zip2('ab', range(10))))

# uncaught StopIteration inside a generator -> RuntimeError
def leaks():
    yield 1
    next(iter([]))


g = leaks()
next(g)
try:
    next(g)
except RuntimeError as e:
    print('RuntimeError:', e, '| cause:', type(e.__cause__).__name__)

def leaks_in_try():
    try:
        yield next(iter([]))
    except KeyError:
        yield 'wrong handler'


try:
    list(leaks_in_try())
except RuntimeError as e:
    print('RuntimeError:', e)

# a RuntimeError from an inner generator is not a StopIteration
def inner_leaks():
    yield next(iter([]))


def outer_catches():
    try:
        yield from inner_leaks()
    except StopIteration:
        yield 'wrong: StopIteration'
    except RuntimeError as e:
        yield 'right: RuntimeError %s' % e


print(list(outer_catches()))

# finally still runs when StopIteration is converted
def finally_runs():
    try:
        yield 1
        raise StopIteration
    finally:
        print('  finally ran')


try:
    list(finally_runs())
except RuntimeError as e:
    print('RuntimeError:', e)

# StopIteration subclass caught by its own class
class MyStop(StopIteration):
    pass


def custom_stop():
    try:
        yield 'start'
        raise MyStop('custom')
    except MyStop as e:
        yield 'caught MyStop %s' % e


print(list(custom_stop()))
