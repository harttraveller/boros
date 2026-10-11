# Bare raise, re-raise after handling, raising stored exceptions.


class E(Exception):
    pass


def bare_reraise():
    try:
        raise E('orig')
    except E:
        raise


try:
    bare_reraise()
except E as e:
    print('re-raised', repr(e.args), type(e).__name__)


def reraise_from_helper():
    def helper():
        raise  # re-raises the exception being handled by the caller
    try:
        raise KeyError('helper')
    except KeyError:
        helper()


try:
    reraise_from_helper()
except KeyError as e:
    print('helper re-raise', e)


def reraise_after_nested():
    try:
        raise E('outer')
    except E:
        try:
            raise ValueError('inner')
        except ValueError:
            pass
        raise  # must re-raise E('outer'), not the inner one


try:
    reraise_after_nested()
except Exception as e:
    print('after nested:', type(e).__name__, e)


def reraise_in_finally_of_handler():
    try:
        raise E('h')
    except E:
        try:
            pass
        finally:
            raise


try:
    reraise_in_finally_of_handler()
except E as e:
    print('finally in handler:', e)

# no active exception
try:
    raise
except RuntimeError as e:
    print('RuntimeError:', e)

# storing an exception and raising it later
saved = None
try:
    raise E('saved')
except E as e:
    saved = e
print(type(saved).__name__, saved.args)
try:
    raise saved
except E as e2:
    print('raised saved again:', e2 is saved)

# raise inside except of a different type keeps context
try:
    try:
        raise E('first')
    except E as first:
        raise ValueError('second')
except ValueError as v:
    print(type(v.__context__).__name__, v.__context__.args)

# re-raise with modified args
try:
    try:
        raise E('a')
    except E as e:
        e.args = ('modified',)
        raise
except E as e:
    print('modified:', e.args, str(e))

# catch, convert to string, re-raise as different type in a loop
results = []
for item in [1, 0, 'x', 2]:
    try:
        try:
            results.append(10 // item)
        except ZeroDivisionError:
            raise
        except TypeError as t:
            results.append('T')
    except ZeroDivisionError as z:
        results.append('Z')
print(results)

# raise from inside lambda/comprehension
try:
    [1 // x for x in (1, 0)]
except ZeroDivisionError as e:
    print('comprehension:', e)

try:
    list(map(lambda x: {}[x], ['key']))
except KeyError as e:
    print('lambda in map:', repr(e))

# exception passes through several frames
def level3():
    raise E('deep')


def level2():
    try:
        level3()
    finally:
        print('level2 finally')


def level1():
    try:
        level2()
    except ValueError:
        print('wrong handler')


try:
    level1()
except E as e:
    print('caught deep:', e)

# exception from a method of a class and from __init__
class Thing:
    def __init__(self, ok):
        if not ok:
            raise E('init failed')
        self.ok = ok

    def act(self):
        raise NotImplementedError('act')


try:
    Thing(False)
except E as e:
    print(e)
try:
    Thing(True).act()
except NotImplementedError as e:
    print('NotImplementedError', e)

# raise in class body
try:
    class Bad:
        raise E('class body')
except E as e:
    print('class body:', e)
