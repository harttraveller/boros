# Non-ASCII identifiers: variables, functions, classes, attributes,
# keyword arguments, and names reached through globals()/getattr().

café = 'coffee'
π = 3.14159
变量 = 42
Δx = 0.5
naïve_count = 3
_ñ = 'underscore n-tilde'
αβγ = [1, 2, 3]
print(café, π, 变量, Δx, naïve_count, _ñ, αβγ)


def grüße(name, *, höflich=False):
    return ('Guten Tag, ' if höflich else 'Hallo, ') + name


print(grüße('Welt'), grüße('Welt', höflich=True))
print(grüße.__name__, grüße.__qualname__)


class Über:
    größe = 7

    def __init__(self):
        self.länge = 3

    def fläche(self):
        return self.größe * self.länge


ü = Über()
print(Über.__name__, ü.länge, ü.fläche(), getattr(ü, 'länge'), Über.größe)
setattr(ü, 'höhe', 9)
print(ü.höhe, sorted(k for k in vars(ü)))
print('café' in globals(), globals()['变量'])
kw = {'höflich': True}
print(grüße('Ihnen', **kw))
λ = lambda ξ: ξ * 2
print(λ(21))
print([ω for ω in range(3)])
print({ключ: значение for ключ, значение in [('a', 1)]})
ns = {}
exec('ñandú = "bird"\nresultado = ñandú.upper()', ns)
print(ns['resultado'])
print(eval('π * 2'))
# identifiers containing digits and combining marks after the first char
x١ = 'arabic-indic digit'
print(x١, len('x١'))
print(str.isidentifier('café'), 'π'.isidentifier(), '1a'.isidentifier(), '_'.isidentifier())
