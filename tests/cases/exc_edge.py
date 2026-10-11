# Edge cases of try statements and handler name binding.


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
def del_name_in_handler():
    try:
        raise E('d')
    except E as e:
        del e
    return 'ok'


@section
def rebind_name_in_handler():
    try:
        raise E('r')
    except E as e:
        e = 'rebound'
    try:
        return e
    except UnboundLocalError as u:
        return 'UnboundLocalError: %s' % u


g_exc = 'global before'


@section
def global_handler_name():
    global g_exc
    try:
        raise E('g')
    except E as g_exc:
        pass
    return 'g_exc' in globals()


@section
def nonlocal_handler_name():
    x = 'before'

    def inner():
        nonlocal x
        try:
            raise E('n')
        except E as x:
            pass
    inner()
    try:
        return x
    except NameError as ne:
        return 'NameError: %s' % ne


@section
def else_not_protected():
    try:
        try:
            pass
        except E:
            return 'wrong: handler caught else exception'
        else:
            raise E('from else')
    except E as e:
        return 'outer caught %s' % e


@section
def exception_in_finally_replaces_return():
    def f():
        try:
            return 'value'
        finally:
            raise E('finally wins')
    try:
        return f()
    except E as e:
        return 'E: %s ctx=%s' % (e, e.__context__)


@section
def exception_in_finally_replaces_exception():
    try:
        try:
            raise KeyError('original')
        finally:
            raise E('replacement')
    except E as e:
        return type(e.__context__).__name__, e.__context__.args


@section
def handler_with_finally():
    log = []
    try:
        try:
            raise E('h')
        except E:
            log.append('handler')
            raise ValueError('from handler')
        finally:
            log.append('finally')
    except ValueError as v:
        log.append('outer %s ctx=%s' % (v, type(v.__context__).__name__))
    return log


@section
def exception_in_handler_type_expression():
    try:
        try:
            raise E('orig')
        except undefined_name_xyz:
            pass
    except NameError as ne:
        return 'NameError: %s ctx=%s' % (ne, type(ne.__context__).__name__)


@section
def raise_non_exception():
    out = []
    for bad in (5, 'str', None, object, [ValueError]):
        try:
            raise bad
        except TypeError as t:
            out.append(str(t))
    return out


@section
def raise_class_with_failing_init():
    class Bad(Exception):
        def __init__(self):
            raise ValueError('init of exception failed')
    try:
        raise Bad
    except ValueError as v:
        return 'ValueError: %s' % v


@section
def exception_in_comprehension_condition():
    try:
        return [x for x in range(5) if 10 // (x - 3)]
    except ZeroDivisionError as z:
        return 'ZeroDivisionError: %s' % z


@section
def try_in_lambda_called_function():
    def safe(f, default):
        try:
            return f()
        except Exception as e:
            return '%s(%s)' % (default, type(e).__name__)
    return [safe(lambda: 1 / 0, 'd'), safe(lambda: [][0], 'i'), safe(lambda: 5, 'x')]


@section
def deep_finally_ordering():
    log = []

    def a():
        try:
            b()
        finally:
            log.append('a')

    def b():
        try:
            c()
        finally:
            log.append('b')

    def c():
        try:
            raise E('c')
        finally:
            log.append('c')
    try:
        a()
    except E:
        log.append('caught')
    return log


@section
def exception_object_reuse():
    err = E('reused')
    results = []
    for i in range(2):
        try:
            raise err
        except E as caught:
            results.append(caught is err)
    return results


@section
def exception_args_with_instances():
    class Payload:
        def __repr__(self):
            return 'Payload()'
    e = E(Payload(), [1, 2])
    return str(e), e.args[1]


@section
def isinstance_issubclass_on_exceptions():
    class Sub(E):
        pass
    s = Sub('s')
    return (isinstance(s, E), isinstance(s, Exception), isinstance(s, BaseException),
            isinstance(s, (KeyError, Sub)), issubclass(Sub, Exception), issubclass(Sub, (KeyError, E)),
            issubclass(Sub, BaseException), isinstance(ValueError(), E))


@section
def exception_type_and_name():
    class Sub(E):
        pass
    s = Sub('s')
    return type(s).__name__, s.__class__.__name__, type(s) is Sub, Sub.__mro__[-3:]
