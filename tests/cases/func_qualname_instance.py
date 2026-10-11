# A class's __qualname__ is not an entry of its __dict__, so instances do not
# see it (a bound-method-like wrapper with __getattr__ forwards it instead).


class Wrapper:
    def __init__(self, f):
        self.f = f

    def __getattr__(self, name):
        return getattr(self.f, name)


def target():
    pass


w = Wrapper(target)
print(w.__qualname__, w.__name__)
print('__qualname__' in Wrapper.__dict__, '__module__' in Wrapper.__dict__)


class B:
    pass


try:
    B().__qualname__
except AttributeError as e:
    print('AttributeError:', e)
print(B.__qualname__, B().__class__.__qualname__)


def outer():
    class Local:
        pass
    return Local


L = outer()
print(L.__qualname__, '__qualname__' in vars(L), type(L.__qualname__).__name__)
