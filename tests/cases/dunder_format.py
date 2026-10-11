# __repr__ / __str__ / __format__ in print, f-strings (with conversions and
# format specs), str.format and %-formatting; result type checks.


class Money:
    def __init__(self, cents):
        self.cents = cents

    def __repr__(self):
        return 'Money(%d)' % self.cents

    def __str__(self):
        return '$%d.%02d' % divmod(self.cents, 100)

    def __format__(self, spec):
        if spec == 'raw':
            return str(self.cents)
        if spec.endswith('c'):
            return format(self.cents, spec[:-1] + 'd')
        return format(str(self), spec)


m = Money(12345)
print(m, repr(m), str(m), [m], (m,), {'k': m})
print(f'{m}', f'{m!r}', f'{m!s}', f'{m!a}', f'{m:raw}', f'{m:>12}', f'{m:*^14}', f'{m:08c}')
w = 12
print(f'{m:>{w}}', f'{m!r:>{w}}', f'{m!s:<{w}}|', f'{m=}', f'{m=:raw}', f'{m=!s}')
print('{}'.format(m), '{!r}'.format(m), '{:raw}'.format(m), '{0:>10}|{0!r:<10}|'.format(m))
print(format(m), format(m, 'raw'), format(m, '6c'))
print('%s %r %a' % (m, m, m), '%(x)s' % {'x': m}, '%-12s|' % m, '%12r|' % (m,))


class OnlyRepr:
    def __repr__(self):
        return '<OnlyRepr>'


class OnlyStr:
    def __str__(self):
        return 'only-str'


o = OnlyRepr()
print(o, str(o), f'{o}', '%s' % o, format(o), f'{o:}', '{}'.format(o))
print(repr(OnlyStr()).startswith('<__main__.OnlyStr object at 0x'), OnlyStr(), f'{OnlyStr()!s}')
print(str([OnlyStr()]).startswith('[<__main__.OnlyStr object'))


class Unicode:
    def __repr__(self):
        return 'Ünï☃'


print(repr(Unicode()), ascii(Unicode()), f'{Unicode()!a}', '%a' % Unicode())


# default __format__ rejects non-empty specs
def attempt(label, f):
    try:
        print(label, '->', f())
    except (TypeError, ValueError) as e:
        print(label, '->', type(e).__name__ + ':', e)


attempt("format(OnlyRepr(), '>5')", lambda: format(OnlyRepr(), '>5'))
attempt("f'{OnlyRepr():>5}'", lambda: f'{OnlyRepr():>5}')
attempt("'{:x}'.format(OnlyStr())", lambda: '{:x}'.format(OnlyStr()))
attempt("f'{OnlyRepr()!r:>12}'", lambda: f'{OnlyRepr()!r:>12}')


# wrong return types
class BadRepr:
    def __repr__(self):
        return 42


class BadStr:
    def __str__(self):
        return None


class BadFormat:
    def __format__(self, spec):
        return 3.5


class StrSubRet:
    def __str__(self):
        class S(str):
            pass
        return S('str subclass')

    def __repr__(self):
        class S(str):
            pass
        return S('repr subclass')


attempt('repr(BadRepr())', lambda: repr(BadRepr()))
attempt('str(BadRepr())', lambda: str(BadRepr()))
attempt('print-ish BadStr', lambda: str(BadStr()))
attempt("'%s' % BadStr()", lambda: '%s' % BadStr())
attempt("f'{BadStr()}'", lambda: f'{BadStr()}')
attempt("f'{BadRepr()!r}'", lambda: f'{BadRepr()!r}')
attempt('format(BadFormat())', lambda: format(BadFormat()))
attempt("f'{BadFormat():x}'", lambda: f'{BadFormat():x}')
attempt("'{}'.format(BadFormat())", lambda: '{}'.format(BadFormat()))
attempt('str(StrSubRet())', lambda: str(StrSubRet()))
attempt('repr(StrSubRet())', lambda: repr(StrSubRet()))
attempt('[repr list]', lambda: repr([BadRepr()]))


# __format__ receives the spec string unchanged; inheritance from str/int
class Spy:
    def __format__(self, spec):
        return '<%s>' % spec


print(f'{Spy()}', f'{Spy():}', f'{Spy():abc}', f'{Spy():{"x"}{1}}', '{:  q }'.format(Spy()))


class MyInt(int):
    def __str__(self):
        return 'MyInt!'


print(MyInt(5), f'{MyInt(5)}', f'{MyInt(5):03d}', '%d' % MyInt(5), '%s' % MyInt(5), format(MyInt(5), 'x'))


class MyStr(str):
    def __format__(self, spec):
        return 'MyStr.__format__(%s)' % spec


print(f'{MyStr("v"):>4}', '{}'.format(MyStr('q')), '%s' % MyStr('pct'))

# %-formatting numeric conversions use __index__/__int__/__float__
class Num:
    def __index__(self):
        return 255

    def __float__(self):
        return 2.5


print('%d %i %x %o %X %f %.1e %g' % (Num(), Num(), Num(), Num(), Num(), Num(), Num(), Num()))
attempt("'%c' % OnlyRepr()", lambda: '%c' % OnlyRepr())
attempt("'%s %s' % OnlyRepr()", lambda: '%s %s' % OnlyRepr())
attempt("format(Num(), 'd')", lambda: format(Num(), 'd'))
