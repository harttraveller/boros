# except* semantics: what propagates after the clauses ran, nested groups,
# the exception seen inside a clause, and type checks of the clauses.
import sys


class AppError(Exception):
    pass


def show(f):
    try:
        f()
    except BaseException as e:
        print(f.__name__, '->', type(e).__name__, repr(e))
    else:
        print(f.__name__, '-> handled')


def unmatched_rest():
    try:
        raise ExceptionGroup('eg', [ValueError(1), TypeError(2)])
    except* KeyError:
        print('not reached')


def reraise_all():
    try:
        raise ExceptionGroup('eg', [ValueError(1), TypeError(2)])
    except* ValueError:
        raise
    except* TypeError:
        raise


def partial():
    try:
        raise ExceptionGroup('eg', [ValueError(1), TypeError(2)])
    except* ValueError as v:
        print('  v:', repr(v))


def new_and_rest():
    try:
        raise ExceptionGroup('eg', [ValueError(1), TypeError(2)])
    except* ValueError as v:
        raise KeyError('new') from None


def raise_leaf():
    try:
        raise ExceptionGroup('eg', [ValueError(1), TypeError(2)])
    except* ValueError as v:
        raise v.exceptions[0]


def nested():
    try:
        raise ExceptionGroup('outer', [ValueError(1), ExceptionGroup('inner', [TypeError(2), ValueError(3)])])
    except* ValueError as v:
        print('  v:', repr(v))
    except* TypeError as t:
        print('  t:', repr(t))
        raise


def match_all_with_base_class():
    try:
        raise ExceptionGroup('eg', [ValueError(1), AppError('a')])
    except* Exception as x:
        print('  x:', x, [type(e).__name__ for e in x.exceptions])


def naked_reraised():
    try:
        raise ValueError('naked')
    except* ValueError as v:
        print('  v:', repr(v), sys.exception() is v)
        raise


def naked_interp_unmatched():
    try:
        raise AppError('app')
    except* TypeError:
        print('not reached')


def handler_raises_in_both():
    try:
        raise ExceptionGroup('eg', [ValueError(1), TypeError(2)])
    except* ValueError:
        raise KeyError('k')
    except* TypeError:
        raise IndexError('i')


def later_clause_type_evaluated():
    try:
        raise ExceptionGroup('eg', [ValueError(1)])
    except* ValueError:
        pass
    except* undefined_name:
        pass


def bad_clause_type():
    try:
        raise ExceptionGroup('eg', [ValueError(1)])
    except* (ValueError, 42):
        pass


def group_clause_type():
    try:
        raise ValueError(1)
    except* (TypeError, BaseExceptionGroup):
        pass


def single_new_exception_is_naked():
    try:
        try:
            raise ExceptionGroup('eg', [ValueError(1)])
        except* ValueError:
            raise KeyError('k')
    except KeyError as k:
        print('  naked:', repr(k), 'context:', repr(k.__context__))


def single_new_exception_with_empty_clause():
    try:
        raise ExceptionGroup('eg', [ValueError(1)])
    except* ValueError:
        raise KeyError('k')
    except* TypeError:
        pass


def generator_star():
    def gen():
        try:
            yield 1
            raise ExceptionGroup('g', [AppError('x'), ValueError('y'), TypeError('z')])
        except* AppError as g:
            yield 'app %d' % len(g.exceptions)
        except* ValueError:
            yield 'value'
        finally:
            yield 'finally'
    try:
        for x in gen():
            print('  gen:', x)
    except ExceptionGroup as g:
        print('  rest:', repr(g))


for f in (unmatched_rest, reraise_all, partial, new_and_rest, raise_leaf, nested, match_all_with_base_class,
          naked_reraised, naked_interp_unmatched, handler_raises_in_both, later_clause_type_evaluated,
          bad_clause_type, group_clause_type, single_new_exception_is_naked, single_new_exception_with_empty_clause,
          generator_star):
    show(f)
