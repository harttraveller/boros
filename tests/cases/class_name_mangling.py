# Private name mangling.

class Account:
    __rate = 0.05            # class-private class attribute

    def __init__(self, balance):
        self.__balance = balance
        self._protected = 'p'
        self.__dunder__ = 'not mangled'

    def __secret(self):
        return 'secret %s' % self.__balance

    def reveal(self):
        return self.__secret(), self.__rate

    @classmethod
    def rate(cls):
        return cls.__rate


a = Account(100)
print(a.reveal(), Account.rate())
print(sorted(vars(a)))
print(a._Account__balance, a._Account__secret())
print('_Account__rate' in Account.__dict__, '_Account__secret' in Account.__dict__)
try:
    a.__balance
except AttributeError as e:
    print('AttributeError:', e)
print(a.__dunder__)
print(getattr(a, '_Account__balance'), hasattr(a, '__balance'))


# subclasses get their own private namespace
class Savings(Account):
    def __init__(self, balance):
        super().__init__(balance)
        self.__balance = 'savings private'

    def both(self):
        return self.__balance, self._Account__balance


s = Savings(5)
print(s.both())
print(sorted(vars(s)))


# leading underscores in class name are stripped for mangling
class _Hidden:
    def __init__(self):
        self.__x = 1


class __Very:
    def __init__(self):
        self.__y = 2


print(sorted(vars(_Hidden())), sorted(vars(__Very())))


# mangling happens in nested functions, lambdas, comprehensions inside a class
class Nest:
    def __init__(self):
        self.__v = 3

    def get(self):
        f = lambda: self.__v
        def inner():
            return self.__v * 2
        return f(), inner(), [self.__v for _ in range(2)]


print(Nest().get())


# mangling of names used in getattr strings does NOT happen
class Str:
    def __init__(self):
        self.__z = 'z'

    def via_getattr(self):
        try:
            return getattr(self, '__z')
        except AttributeError as e:
            return 'AttributeError: ' + str(e)


print(Str().via_getattr())


# mangled names for globals referenced inside a class body
__glob = 'module-level __glob'


class UsesGlobal:
    def m(self):
        try:
            return __glob
        except NameError as e:
            return 'NameError: ' + str(e)


print(UsesGlobal().m())

_UsesGlobal2__glob = 'mangled global'


class UsesGlobal2:
    def m(self):
        return __glob


print(UsesGlobal2().m())


# keyword arguments and parameter names are mangled too
class Kw:
    def f(self, __p=1):
        return __p

    def g(self):
        return self.f(__p=5)


print(Kw().f(), Kw().f(_Kw__p=7))
try:
    Kw().g()       # keyword names in calls are not mangled
except TypeError as e:
    print('TypeError:', e)


# mangled attribute names in a nested class use the innermost class
class OuterM:
    class InnerM:
        def __init__(self):
            self.__a = 1

    def __init__(self):
        self.__b = 2


print(sorted(vars(OuterM.InnerM())), sorted(vars(OuterM())))


# __slots__ and mangling
class SlotM:
    __slots__ = ('__q',)

    def __init__(self):
        self.__q = 'q'


print(SlotM()._SlotM__q)
