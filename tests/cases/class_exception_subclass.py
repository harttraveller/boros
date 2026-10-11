# User exception classes: custom __init__, __str__, attributes, hierarchy.

class AppError(Exception):
    """Base application error."""


class NotFound(AppError):
    def __init__(self, key):
        super().__init__('not found: %r' % (key,))
        self.key = key


class Invalid(AppError, ValueError):
    def __init__(self, field, reason):
        self.field = field
        self.reason = reason
        super().__init__(field, reason)

    def __str__(self):
        return '%s is invalid (%s)' % (self.field, self.reason)


class WithRepr(Exception):
    def __repr__(self):
        return 'WithRepr<%s>' % (self.args,)


try:
    raise NotFound('k1')
except AppError as e:
    print(type(e).__name__, e, e.args, e.key)
    print(isinstance(e, Exception), isinstance(e, NotFound), isinstance(e, ValueError))

try:
    raise Invalid('age', 'negative')
except ValueError as e:
    print(type(e).__name__, str(e), e.args, e.field, e.reason)
    print([c.__name__ for c in type(e).__mro__])

try:
    raise WithRepr(1, 2)
except Exception as e:
    print(repr(e), str(e), e.args)

# exceptions with no args and with many args
print(str(AppError()), AppError().args)
print(str(AppError('a', 'b')))

# catching by tuple and ordering
for exc in (NotFound('a'), Invalid('f', 'r'), KeyError('k')):
    try:
        raise exc
    except (Invalid, KeyError) as e:
        print('caught specific', type(e).__name__)
    except AppError as e:
        print('caught base', type(e).__name__)

# attributes set on exception instances and class attributes
class Coded(Exception):
    code = 500

    def __init__(self, msg, code=None):
        super().__init__(msg)
        if code is not None:
            self.code = code


try:
    raise Coded('server', 404)
except Coded as e:
    print(e, e.code, Coded.code, e.__class__.__name__)

try:
    raise Coded('server')
except Coded as e:
    print(e, e.code)

# chaining with user exceptions
try:
    try:
        raise NotFound('inner')
    except NotFound as inner:
        raise AppError('outer') from inner
except AppError as e:
    print(e, type(e.__cause__).__name__, e.__cause__.key, e.__suppress_context__)

try:
    try:
        {}['x']
    except KeyError:
        raise NotFound('ctx')
except NotFound as e:
    print(e, type(e.__context__).__name__, e.__cause__)

# raising the class itself
try:
    raise AppError
except AppError as e:
    print('class raised', type(e).__name__, e.args)

# exception with __init__ that does not call super().__init__
class NoSuper(Exception):
    def __init__(self, a, b):
        self.a = a
        self.b = b


try:
    raise NoSuper(1, 2)
except NoSuper as e:
    print(e.args, e.a, e.b, str(e))

# BaseException subclass is not caught by except Exception
class Stop(BaseException):
    pass


try:
    try:
        raise Stop('halt')
    except Exception:
        print('wrong handler')
except BaseException as e:
    print('BaseException handler', type(e).__name__, e)

# exception instances are regular objects: methods, properties
class Rich(Exception):
    def __init__(self, items):
        super().__init__(len(items))
        self.items = items

    @property
    def count(self):
        return len(self.items)

    def summary(self):
        return 'Rich(%d)' % self.count


r = Rich([1, 2, 3])
print(r.summary(), r.args, r.count)

# issubclass checks for exception hierarchy
print(issubclass(Invalid, ValueError), issubclass(NotFound, LookupError), issubclass(Stop, Exception))

# uncaught user exception at the end
raise Invalid('name', 'empty')
