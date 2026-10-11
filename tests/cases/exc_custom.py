# Custom exception hierarchies with __init__/__str__/__repr__ overrides; args, str(), repr().


class Base(Exception):
    pass


class WithInit(Base):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


class WithStr(Base):
    def __str__(self):
        return 'WithStr<%s>' % ','.join(map(str, self.args))


class WithRepr(Base):
    def __repr__(self):
        return 'WithRepr!'


class NoSuperInit(Base):
    def __init__(self, a, b):
        self.a = a
        self.b = b


class Multi(ValueError, Base):
    pass


class KeyLike(KeyError):
    pass


class Leaf(WithInit):
    def __init__(self):
        super().__init__(7, 'leaf message')


for e in [Base(), Base('one'), Base('a', 2), WithInit(404, 'not found'), WithStr(1, 2),
          WithRepr('r'), NoSuperInit(1, 2), Multi('m'), KeyLike('kk'), Leaf()]:
    print(type(e).__name__, '|', str(e), '|', repr(e), '|', e.args)

e = WithInit(500, 'server')
print(e.code, e.args, isinstance(e, Base), isinstance(e, Exception), issubclass(WithInit, Base))
print(Multi.__mro__[1:3] == (ValueError, Base), isinstance(Multi('x'), ValueError))
print([c.__name__ for c in Leaf.__mro__])

try:
    raise Multi('multi')
except Base as caught:
    print('caught Multi as Base:', caught, type(caught).__name__)

try:
    raise Multi('multi2')
except ValueError as caught:
    print('caught Multi as ValueError:', caught)

try:
    raise KeyLike('kl')
except LookupError as caught:
    print('KeyLike via LookupError', repr(caught), str(caught))

# args can be replaced
e = Base('first')
e.args = ('second', 2)
print(e.args, str(e), repr(e))
e2 = ValueError('v')
e2.args = ('w',)
print(e2.args, str(e2))

# attributes on exceptions
e = Base('attrs')
e.extra = [1, 2]
print(e.extra, hasattr(e, 'extra'), getattr(e, 'nothing', 'default'))
try:
    e.nothing
except AttributeError as ae:
    print('AttributeError:', ae)

# exception equality and hashing are identity based
a = Base('same')
b = Base('same')
print(a == b, a == a, a != b, len({a, b, a}))

# __str__ using attributes
class Detailed(Exception):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        super().__init__(name, value)

    def __str__(self):
        return '%s=%r' % (self.name, self.value)


try:
    raise Detailed('limit', 10)
except Detailed as d:
    print(d, repr(d), d.args, '%s' % d, f'{d}', '{}'.format(d), str([d]) == '[' + repr(d) + ']')

# with_traceback returns self
e = Base('wt')
print(e.with_traceback(None) is e)

# raising an exception class instantiates it
try:
    raise WithStr
except WithStr as w:
    print('class raised:', repr(w), w.args, str(w))

# BaseException subclasses are not caught by except Exception
class Fatal(BaseException):
    pass


try:
    try:
        raise Fatal('fatal')
    except Exception:
        print('wrong')
except BaseException as be:
    print('BaseException caught', type(be).__name__, be)

# exception class attributes and methods
class Coded(Exception):
    default_code = 99

    def describe(self):
        return 'Coded(%d): %s' % (self.default_code, self.args[0])

    @classmethod
    def make(cls, msg):
        return cls(msg)


c = Coded.make('made')
print(c.describe(), type(c).__name__, Coded.default_code)

# exception with keyword-only init
class KwErr(Exception):
    def __init__(self, *, reason):
        super().__init__(reason)
        self.reason = reason


try:
    raise KwErr(reason='kw')
except KwErr as k:
    print(k.reason, k.args)

# repr of builtin exceptions with several args
print(repr(OSError(2, 'No such file')), str(OSError(2, 'No such file')))
print(repr(KeyError('k')), str(KeyError('k')), str(KeyError('a', 'b')), str(KeyError()))
print(repr(UnicodeError('u')), repr(StopIteration(5)), StopIteration(5).value)
print(repr(SystemExit(3)), SystemExit(3).code, SystemExit().code, SystemExit(1, 2).code)

# subclass of OSError: errno/strerror attributes
class MyOS(OSError):
    pass


m = MyOS(13, 'Permission denied')
print(m.errno, m.strerror, str(m), type(m).__name__)

# exception __class__ and type
print(type(Base('t')) is Base, Base('t').__class__.__name__, Base.__name__, Base.__qualname__)
print(Base.__bases__, WithInit.__base__.__name__)

# BaseException.__repr__ reached through super() and called unbound
class ReprViaSuper(Exception):
    def __repr__(self):
        return 'custom ' + super().__repr__()


print(repr(ReprViaSuper(1, 2)), BaseException.__repr__(ReprViaSuper('x')), Exception.__repr__(Base()))
