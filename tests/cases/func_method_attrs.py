# Bound methods forward __doc__ and __module__ to the underlying function.
import _func_mod


class C:
    def m(self):
        "mdoc"
        return 1

    def nodoc(self):
        return 2


c = C()
print(c.m.__doc__, c.nodoc.__doc__, C.m.__doc__)
print(c.m.__module__, C.m.__module__)
t = _func_mod.Thing()
print(t.method.__doc__, t.method.__module__, _func_mod.Thing.method.__module__)
print(_func_mod.helper.__module__, _func_mod.make_closure(1).__module__, _func_mod.make_closure(1)(2))
print(t.method.__name__, t.method.__qualname__)
