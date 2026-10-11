# Operator and delimiter tokens, written with and without spaces.

a, b = 7, 3
print(a+b, a-b, a*b, a/b, a//b, a%b, a**b, a<<b, a>>b, a&b, a|b, a^b, ~a, -a, +a)
print(a<b, a>b, a<=b, a>=b, a==b, a!=b, a is b, a is not b, a in [7], a not in [7])
print(a+-b, a- -b, a--b, a+ +b, a**-1, -a**2, (-a)**2, 2**3**2, not a==b)
x = 10
x+=1; x-=2; x*=3; x//=2; x%=7; x**=2; x<<=2; x>>=1; x&=0xff; x|=1; x^=3
print(x)
y = 7.0
y/=2
print(y)


class M:
    def __init__(self, v):
        self.v = v

    def __matmul__(self, other):
        return M(self.v * other.v)

    def __imatmul__(self, other):
        self.v += other.v
        return self


m = M(2)@M(3)
print(m.v)
m@=M(4)
print(m.v)
print(...,  Ellipsis is ..., [...])
lst = list(range(10))
print(lst[::2], lst[1:-1:3], lst[:], lst[-1], lst[:-7], lst[::-1][:2])
d = {'k':1}
print(d['k'], {**d, 'j':2}, [*lst[:2], *'ab'], (*'xy',))


def f(p, /, q, *, r=1) -> int:
    return p+q+r


print(f(1, 2), f(1, q=2, r=3), f.__annotations__ if False else 'ann')
if (n:=5)>3: print('walrus', n)
print([y for x in [1, 2] if (y:=x*10)>10])
print(1<2<3, 3>2>1, 1<2>1, 1==1.0!=2)
print((lambda:0)(), (lambda *a,**k:(a,k))(1, z=2))
print(a if a>b else b, a and b, a or b, not a)
print(0b1|0o2|0x4, 1_0+0_0, 1e1*2.5j)
s = 'abc'
print(s[0]+s[-1], s*2, 2*s, s in 'xabcx', s.upper().lower())
@staticmethod
def deco(): pass
print(type(deco).__name__)
print(a<<1|b>>1&a^b)
