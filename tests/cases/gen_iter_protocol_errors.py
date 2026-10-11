"""Iterator protocol validation for interpreted classes: iter() must reject
an __iter__ that returns a non-iterator, and __iter__ = None must make a
class non-iterable even if it defines __getitem__."""


class NoNext:
    def __iter__(self):
        return self


try:
    iter(NoNext())
    print('no error from iter()')
except TypeError as e:
    print('TypeError', e)

try:
    for x in NoNext():
        pass
except TypeError as e:
    print('TypeError', e)

class Other:
    pass


class ReturnsOther:
    def __iter__(self):
        return Other()


try:
    list(ReturnsOther())
except TypeError as e:
    print('TypeError', e)

# __iter__ = None blocks the __getitem__ fallback
class Blocked:
    __iter__ = None

    def __getitem__(self, i):
        if i > 2:
            raise IndexError(i)
        return i


try:
    print(list(Blocked()))
except TypeError as e:
    print('TypeError', e)
try:
    print(1 in Blocked())
except TypeError as e:
    print('TypeError', e)

# a subclass can re-enable iteration
class Unblocked(Blocked):
    def __iter__(self):
        return iter([7, 8])


print(list(Unblocked()))

# the __getitem__ fallback still works when __iter__ is simply absent
class Fallback:
    def __getitem__(self, i):
        if i > 2:
            raise IndexError(i)
        return i * 3


print(list(Fallback()), 6 in Fallback())

# membership test on a non-iterable instance without __contains__
class Plain:
    pass


try:
    print(1 in Plain())
except TypeError as e:
    print('TypeError', e)
