# Exception chaining: raise X from Y, from None, implicit __context__.


def tname(e):
    return None if e is None else type(e).__name__


def show(e):
    print(type(e).__name__, str(e), '| cause:', tname(e.__cause__), '| context:', tname(e.__context__),
          '| suppress:', e.__suppress_context__)


class AppError(Exception):
    pass


class DbError(AppError):
    pass


try:
    try:
        {}['missing']
    except KeyError as k:
        raise AppError('wrapped') from k
except AppError as e:
    show(e)
    print(repr(e.__cause__), e.__cause__ is e.__context__)

try:
    try:
        1 / 0
    except ZeroDivisionError:
        raise DbError('implicit')
except AppError as e:
    show(e)
    print(isinstance(e.__context__, ZeroDivisionError), e.__context__.args)

try:
    try:
        raise DbError('inner')
    except DbError:
        raise ValueError('outer') from None
except ValueError as e:
    show(e)
    print(type(e.__context__).__name__, e.__context__.args)

# cause is an interpreted exception instance; identity is preserved
try:
    original = DbError('orig', 42)
    try:
        raise original
    except DbError as d:
        raise AppError('top') from d
except AppError as e:
    print(e.__cause__ is original, e.__cause__.args, isinstance(e.__cause__, DbError))

# raise from a class (instantiated)
try:
    raise AppError('cls cause') from DbError
except AppError as e:
    show(e)

# context set by exception raised in finally
try:
    try:
        raise KeyError('first')
    finally:
        raise IndexError('second')
except IndexError as e:
    show(e)
    print(e.__context__.args)

# context set for exception raised in a function called from handler


def helper():
    raise RuntimeError('from helper')


try:
    try:
        raise TypeError('t')
    except TypeError:
        helper()
except RuntimeError as e:
    show(e)

# chains of three
try:
    try:
        try:
            raise ValueError(1)
        except ValueError:
            raise KeyError(2)
    except KeyError:
        raise AppError(3)
except AppError as e:
    chain = []
    x = e
    while x is not None:
        chain.append(type(x).__name__)
        x = x.__context__
    print(chain)

# manual assignment of __cause__ / __context__
e = AppError('manual')
e.__cause__ = KeyError('c')
print(tname(e.__cause__), e.__suppress_context__)
e.__suppress_context__ = False
e.__context__ = DbError('ctx')
print(tname(e.__context__), type(e.__context__) is DbError)

# raise from non-exception is a TypeError
try:
    raise AppError('x') from 5
except TypeError as t:
    print('TypeError:', t)

# no context when the handler finished before raise
try:
    try:
        raise ValueError
    except ValueError:
        pass
    raise KeyError('k')
except KeyError as e:
    show(e)

# re-raising the same exception does not make it its own context
try:
    try:
        raise AppError('same')
    except AppError as e:
        raise e
except AppError as e2:
    show(e2)

# context of exception in else-block of try within handler
try:
    try:
        raise ValueError('v')
    except ValueError:
        try:
            pass
        except Exception:
            pass
        else:
            raise DbError('in else')
except DbError as e:
    show(e)

# __context__ when raising in nested handler of a different exception
try:
    try:
        raise ValueError('outer-ctx')
    except ValueError:
        try:
            raise KeyError('inner-ctx')
        except KeyError:
            pass
        raise AppError('after inner')
except AppError as e:
    show(e)
    print(e.__context__.args)
