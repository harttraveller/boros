# Instances of a __slots__ class stored as class attributes are plain values,
# not descriptors (they have no __get__/__set__/__delete__).

class Token:
    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'Token(%r)' % self.name


class Grammar:
    PLUS = Token('+')
    MINUS = Token('-')

    def first(self):
        return self.PLUS


print(Grammar.PLUS, Grammar().MINUS, Grammar().first())
print(getattr(Grammar, 'PLUS', 'missing'), hasattr(Grammar, 'MINUS'))
print(Grammar.__dict__['PLUS'] is Grammar.PLUS)
g = Grammar()
g.PLUS = Token('instance')
print(g.PLUS, Grammar.PLUS)
del g.PLUS
print(g.PLUS)
