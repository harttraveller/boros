# Interpreted functions and bound methods are instances of types.FunctionType
# and types.MethodType.
import types


def f():
    pass


class C:
    def m(self):
        pass

    @staticmethod
    def s():
        pass

    @classmethod
    def c(cls):
        pass


lam = lambda: 0
print(isinstance(f, types.FunctionType), isinstance(lam, types.LambdaType), isinstance(C.m, types.FunctionType))
print(isinstance(C().m, types.MethodType), isinstance(C.c, types.MethodType), isinstance(C.s, types.FunctionType))
print(type(f) is types.FunctionType, type(C().m) is types.MethodType, type(lam) == types.FunctionType)
print(isinstance(len, types.FunctionType), isinstance(f, types.BuiltinFunctionType), isinstance(C().m, types.FunctionType))
print(isinstance(f, (int, types.FunctionType)), issubclass(type(f), types.FunctionType))


def dispatch(x):
    if isinstance(x, types.MethodType):
        return 'method'
    if isinstance(x, types.FunctionType):
        return 'function'
    if callable(x):
        return 'callable'
    return 'other'


print([dispatch(x) for x in (f, lam, C().m, C.m, len, C, 1)])
