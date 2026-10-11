# Interpreted functions are descriptors: __get__ binds them, which host code
# such as functools.singledispatchmethod relies on.
import functools
import types


class K:
    def __init__(self, v):
        self.v = v


def get_v(self):
    return self.v


k = K(7)
bound = get_v.__get__(k, K)
print(bound(), bound.__self__ is k, bound.__func__ is get_v)
print(get_v.__get__(None, K) is get_v)
m = types.MethodType(get_v, k)
print(m(), m.__self__ is k)


class SD:
    @functools.singledispatchmethod
    def f(self, x):
        return 'obj'

    @f.register(int)
    def _(self, x):
        return 'int'

    @f.register(str)
    def _(self, x):
        return 'str'


print(SD().f(1), SD().f('s'), SD().f(1.5))


# bound methods stored as class attributes stay bound
class O:
    def meth(self):
        return 'o'


o = O()


class A:
    m = o.meth
    c = get_v.__call__


print(A().m(), A.m(), A().m.__self__ is o, A().c(k))
