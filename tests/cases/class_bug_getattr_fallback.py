# An AttributeError raised while computing an attribute through a property
# or descriptor __get__ makes Python fall back to __getattr__.

class Fallback:
    @property
    def broken(self):
        raise AttributeError('inner')

    @property
    def fine(self):
        return 'fine'

    def __getattr__(self, name):
        return 'fallback for ' + name


f = Fallback()
print(f.fine)
print(f.broken)
print(getattr(f, 'broken'), hasattr(f, 'broken'))


class Desc:
    def __get__(self, obj, owner):
        if obj is None:
            return self
        raise AttributeError('desc says no')


class UsesDesc:
    d = Desc()

    def __getattr__(self, name):
        return '__getattr__(%s)' % name


print(UsesDesc().d)


# the classic lazy-attribute pattern relying on this
class Lazy:
    @property
    def value(self):
        return self._value          # missing -> AttributeError -> __getattr__

    def __getattr__(self, name):
        if name == '_value':
            return 'computed'
        raise AttributeError(name)


print(Lazy().value)


# without __getattr__, the original error propagates
class NoFallback:
    @property
    def broken(self):
        raise AttributeError('original message')


try:
    NoFallback().broken
except AttributeError as e:
    print('AttributeError:', e)
