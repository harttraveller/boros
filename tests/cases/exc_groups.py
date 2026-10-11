# Exception groups and except* (simple cases).


class AppError(Exception):
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
def construct():
    eg = ExceptionGroup('many', [ValueError(1), TypeError(2)])
    return (str(eg), [type(x).__name__ for x in eg.exceptions], eg.message,
            isinstance(eg, Exception), type(eg).__name__)


@section
def construct_with_interp():
    eg = ExceptionGroup('interp', [AppError('a'), KeyError('k')])
    return [type(x).__name__ for x in eg.exceptions], isinstance(eg.exceptions[0], AppError)


@section
def split_and_subgroup():
    eg = ExceptionGroup('g', [ValueError(1), TypeError(2), ValueError(3)])
    match, rest = eg.split(ValueError)
    sub = eg.subgroup(TypeError)
    return ([e.args for e in match.exceptions], [e.args for e in rest.exceptions],
            [e.args for e in sub.exceptions])


@section
def except_star_host():
    log = []
    try:
        raise ExceptionGroup('eg', [ValueError('v'), TypeError('t'), ValueError('w')])
    except* ValueError as g:
        log.append(('V', [e.args[0] for e in g.exceptions]))
    except* TypeError as g:
        log.append(('T', [e.args[0] for e in g.exceptions]))
    return log


@section
def except_star_interp():
    log = []
    try:
        raise ExceptionGroup('eg', [AppError('a'), ValueError('v')])
    except* AppError as g:
        log.append(('App', [type(e).__name__ for e in g.exceptions]))
    except* ValueError as g:
        log.append(('V', len(g.exceptions)))
    return log


@section
def except_star_naked_exception():
    out = []
    try:
        raise AppError('naked')
    except* AppError as g:
        out.append((type(g).__name__, [type(e).__name__ for e in g.exceptions], g.message))
    return out


@section
def except_star_unhandled_rest():
    try:
        try:
            raise ExceptionGroup('eg', [ValueError(1), KeyError(2)])
        except* ValueError:
            pass
    except ExceptionGroup as rest:
        return [type(e).__name__ for e in rest.exceptions]


@section
def plain_except_catches_group():
    try:
        raise ExceptionGroup('eg', [ValueError(1)])
    except ExceptionGroup as g:
        return repr(g)


@section
def except_star_naked_unmatched():
    try:
        try:
            raise ValueError(1)
        except* TypeError:
            pass
    except ValueError as e:
        return 'naked re-raised as %s' % type(e).__name__


@section
def except_star_naked_bare_raise():
    try:
        try:
            raise ValueError(2)
        except* ValueError:
            raise
    except BaseException as e:
        return type(e).__name__, repr(e)


@section
def except_star_handler_raises_new():
    try:
        try:
            raise ExceptionGroup('eg', [ValueError(1), KeyError(2)])
        except* ValueError:
            raise TypeError('new')
    except BaseException as e:
        return type(e).__name__, repr(e)


@section
def except_star_reraise_all():
    try:
        try:
            raise ExceptionGroup('eg', [ValueError(1), KeyError(2)])
        except* ValueError:
            raise
    except ExceptionGroup as e:
        return repr(e)


@section
def except_star_group_type_rejected():
    try:
        try:
            raise ValueError(3)
        except* ExceptionGroup:
            pass
    except TypeError as e:
        return 'TypeError: %s' % e


@section
def except_star_tuple_and_else_finally():
    log = []
    for exc in (None, ExceptionGroup('g', [KeyError('k'), IndexError('i')])):
        try:
            if exc is not None:
                raise exc
        except* (KeyError, IndexError) as g:
            log.append(sorted(type(e).__name__ for e in g.exceptions))
        else:
            log.append('else')
        finally:
            log.append('finally')
    return log


@section
def except_star_in_generator():
    def gen():
        try:
            yield 1
            raise ExceptionGroup('in gen', [AppError('x'), ValueError('y')])
        except* AppError as g:
            yield 'app %d' % len(g.exceptions)
        except* ValueError:
            yield 'value'
    return list(gen())
