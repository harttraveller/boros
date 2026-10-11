# Host library code setting attributes on instances of interpreted classes
# (functools.update_wrapper on a class-based decorator, setattr via
# operator/functools helpers).
import functools


class CountCalls:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.calls = 0

    def __call__(self, *a):
        self.calls += 1
        return self.__wrapped__(*a)


@CountCalls
def add(a, b):
    """adds two numbers"""
    return a + b


print(add(1, 2), add(3, 4), add.calls, add.__name__, add.__doc__, add.__qualname__)
print(sorted(k for k in vars(add) if not k.startswith('_')))


class Validated:
    def __setattr__(self, name, value):
        if name == 'bad':
            raise ValueError('bad attribute')
        object.__setattr__(self, name, value)


v = Validated()
functools.partial(setattr, v)('x', 1)
print(v.x)
try:
    functools.partial(setattr, v)('bad', 1)
except ValueError as e:
    print('ValueError:', e)
