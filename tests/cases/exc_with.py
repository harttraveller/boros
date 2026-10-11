# with statements: __enter__/__exit__ order, suppression, exceptions in enter/exit.
log = []


class CM:
    def __init__(self, name, suppress=False, fail_enter=False, fail_exit=False):
        self.name = name
        self.suppress = suppress
        self.fail_enter = fail_enter
        self.fail_exit = fail_exit

    def __enter__(self):
        log.append('enter ' + self.name)
        if self.fail_enter:
            raise RuntimeError('enter failed: ' + self.name)
        return self.name.upper()

    def __exit__(self, et, ev, tb):
        log.append('exit %s %s %s %s' % (self.name, et.__name__ if et else None,
                                        ev.args if ev is not None else None, tb is not None))
        if self.fail_exit:
            raise KeyError('exit failed: ' + self.name)
        return self.suppress


class MyErr(Exception):
    pass


def run(label, f):
    log.clear()
    try:
        r = f()
        log.append('result %r' % (r,))
    except Exception as e:
        log.append('raised %s %s ctx=%s' % (type(e).__name__, e.args,
                                             type(e.__context__).__name__ if e.__context__ else None))
    print(label, log)


def normal():
    with CM('a') as v:
        log.append('body ' + v)
    return 'done'


def raising():
    with CM('a'):
        raise MyErr('in body')


def suppressing():
    with CM('a', suppress=True):
        raise MyErr('suppressed')
    return 'after suppress'


def host_error_suppressed():
    with CM('a', suppress=True):
        {}['k']
    return 'after host suppress'


def multi():
    with CM('a') as x, CM('b') as y:
        log.append('body %s %s' % (x, y))
        raise ValueError('multi')


def multi_inner_suppress():
    with CM('a'), CM('b', suppress=True):
        raise ValueError('inner suppress')
    return 'continued'


def enter_fails():
    with CM('a'), CM('b', fail_enter=True):
        log.append('never')


def exit_fails():
    with CM('a', fail_exit=True):
        raise MyErr('original')


def exit_fails_no_exc():
    with CM('a', fail_exit=True):
        log.append('body ok')


def return_inside():
    with CM('a'):
        return 'returned'


def loop_control():
    out = []
    for i in range(4):
        with CM(str(i)):
            if i == 1:
                continue
            if i == 3:
                break
            out.append(i)
    return out


def nested_with():
    with CM('outer'):
        with CM('inner', suppress=True):
            raise MyErr('deep')
        log.append('between')
    return 'nested ok'


def truthy_suppress():
    class Truthy(CM):
        def __exit__(self, *a):
            CM.__exit__(self, *a)
            return 'yes'
    with Truthy('t'):
        raise MyErr('truthy')
    return 'truthy suppressed'


def falsy_value():
    class Falsy(CM):
        def __exit__(self, *a):
            CM.__exit__(self, *a)
            return 0
    with Falsy('f'):
        raise MyErr('falsy')


def not_a_cm():
    with 42:
        pass


def missing_exit():
    class OnlyEnter:
        def __enter__(self):
            return self
    with OnlyEnter():
        pass


def target_unpack():
    class Pair:
        def __enter__(self):
            return (1, 2)

        def __exit__(self, *a):
            return False
    with Pair() as (p, q):
        return p + q


def exit_sees_instance():
    seen = []

    class Watch:
        def __enter__(self):
            return self

        def __exit__(self, et, ev, tb):
            seen.append((et is MyErr, isinstance(ev, MyErr), type(ev).__name__, ev.args))
            return True
    with Watch():
        raise MyErr('seen', 1)
    return seen


run('normal', normal)
run('raising', raising)
run('suppressing', suppressing)
run('host_error_suppressed', host_error_suppressed)
run('multi', multi)
run('multi_inner_suppress', multi_inner_suppress)
run('enter_fails', enter_fails)
run('exit_fails', exit_fails)
run('exit_fails_no_exc', exit_fails_no_exc)
run('return_inside', return_inside)
run('loop_control', loop_control)
run('nested_with', nested_with)
run('truthy_suppress', truthy_suppress)
run('falsy_value', falsy_value)
run('not_a_cm', not_a_cm)
run('missing_exit', missing_exit)
run('target_unpack', target_unpack)
run('exit_sees_instance', exit_sees_instance)

# file objects as context managers (host __exit__)
import os
import tempfile
path = os.path.join(tempfile.gettempdir(), 'boros_exc_with_%d.txt' % os.getpid())
try:
    with open(path, 'w') as fh:
        fh.write('data')
        raise MyErr('while writing')
except MyErr as e:
    print('file closed after error:', fh.closed, e)
with open(path) as fh:
    print(fh.read())
os.remove(path)
