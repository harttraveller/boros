# Host code reading __doc__ / __module__ of interpreted callables, instances
# and classes (property(), functools.update_wrapper, inspect.getdoc).
import functools
import inspect
import _func_mod


class Doc:
    "my doc"

    def __call__(self, o):
        return 1


class Plain:
    def __call__(self, o):
        return 2


print(property(Doc()).__doc__)
print(property(Plain()).__doc__)


def wrapper():
    pass


functools.update_wrapper(wrapper, Doc())
print(wrapper.__doc__, wrapper.__module__)
functools.update_wrapper(wrapper, _func_mod.Thing())
print(wrapper.__doc__, wrapper.__module__)
print(inspect.getdoc(Doc), inspect.getdoc(Doc()), inspect.getdoc(_func_mod.Thing))
print(inspect.getdoc(Plain))
