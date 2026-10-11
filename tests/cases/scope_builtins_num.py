import math

print(round(2.5), round(3.5), round(-0.5), round(2.675, 2), round(1234, -2), round(7), type(round(2.0)).__name__)
print(round(1.5, None), round(0.125, 2))
print(divmod(17, 5), divmod(-17, 5), divmod(17.5, 5), divmod(-7, -2))
print(pow(2, 10), pow(2, 10, 1000), pow(3, -1, 7), pow(2.0, 0.5) == math.sqrt(2), pow(-8, 1 / 3).real > 0)
try:
    pow(2, 3, 0)
except ValueError as e:
    print('ValueError:', e)
print(abs(-3), abs(-2.5), abs(3 - 4j), abs(True))
print(chr(65), chr(0x263A), ord('a'), ord('€'))
try:
    ord('ab')
except TypeError as e:
    print('TypeError:', e)
try:
    chr(-1)
except ValueError as e:
    print('ValueError:', e)
print(hex(255), oct(8), bin(5), hex(-1), bin(0))
print(format(3.14159, '.2f'), format(42, '08b'), format(1234567, ','), format('x', '>4'), format(0.5, '%'))
print(int('ff', 16), int('0o17', 0), int(3.9), int(-3.9), float('1e3'), float('-inf'), complex(1, 2))
print(int('  42  '), float(' 2.5 '), bool(0.0), bool('0'))
try:
    int('x1')
except ValueError as e:
    print('ValueError:', e)


class Num:
    def __init__(self, v):
        self.v = v

    def __index__(self):
        return self.v

    def __round__(self, nd=None):
        return 'round(%r, %r)' % (self.v, nd)

    def __abs__(self):
        return 'abs!'

    def __divmod__(self, o):
        return ('divmod', self.v, o)

    def __rdivmod__(self, o):
        return ('rdivmod', o, self.v)

    def __pow__(self, e, mod=None):
        return ('pow', self.v, e, mod)

    def __rpow__(self, b):
        return ('rpow', b, self.v)

    def __format__(self, spec):
        return 'Num<%s>' % spec

    def __neg__(self):
        return Num(-self.v)

    def __repr__(self):
        return 'Num(%d)' % self.v


n = Num(10)
print(hex(n), oct(n), bin(n), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11][n], list(range(n))[-1])
print(round(n), round(n, 3), abs(n), divmod(n, 3), divmod(3, n))
print(pow(n, 2), pow(n, 2, 5), 2 ** n, n ** 3)
print(format(n, 'xyz'), '{:>5}'.format(n), f'{n:abc}', -n)
print(math.floor(2.7), math.ceil(2.1), math.trunc(-2.7), int(n), operator_index if False else '')


class F:
    def __float__(self):
        return 2.5

    def __int__(self):
        return 7


print(float(F()), int(F()), math.sqrt(F()) == math.sqrt(2.5))
try:
    hex(F())
except TypeError as e:
    print('TypeError:', e)
try:
    abs('x')
except TypeError as e:
    print('TypeError:', e)
try:
    round('x')
except TypeError as e:
    print('TypeError:', e)
print(max(1, 2.5), min(True, 0), sum([True, True]), 7 // 2, -7 // 2, 7 % -3, 2 ** -1)
print(math.isclose(0.1 + 0.2, 0.3), math.gcd(12, 18), math.lcm(4, 6), math.prod([1, 2, 3, 4]), math.fsum([0.1] * 10))
print(math.comb(5, 2), math.perm(5, 2), math.factorial(6), math.inf > 1e308, math.isnan(float('nan')))
print(math.log(math.e), math.log2(8), math.log10(1000), round(math.hypot(3, 4), 3), math.copysign(1, -0.0))
