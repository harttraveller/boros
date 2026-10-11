# Host library code reading __doc__ / __module__ from an instance of an
# interpreted class must see the interpreted class's values.
import functools


class Getter:
    """Getter doc"""

    def __call__(self, obj):
        return 'got'


class Holder:
    p = property(Getter())        # property() copies fget.__doc__


print(Holder.p.__doc__)
print(Holder().p)


class Callable:
    """Callable doc"""
    __module__ = 'some.module'

    def __call__(self):
        return 1


w = functools.update_wrapper(lambda: 0, Callable())
print(w.__doc__, w.__module__)


class NoDoc:
    pass


w2 = functools.update_wrapper(lambda: 0, NoDoc())
print(w2.__doc__, w2.__module__)
print(NoDoc().__doc__, NoDoc().__module__, Callable().__doc__)
