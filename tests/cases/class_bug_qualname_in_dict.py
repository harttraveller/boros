# __qualname__ must not be left in the class namespace: it is a property of
# the type, not a class attribute, so instances do not see it.

class C:
    def m(self):
        pass


print('__qualname__' in C.__dict__, '__qualname__' in vars(C))
print(C.__qualname__, C.m.__qualname__)
try:
    print(C().__qualname__)
except AttributeError as e:
    print('AttributeError:', e)
print(hasattr(C(), '__qualname__'), getattr(C(), '__qualname__', 'no instance qualname'))


class Outer:
    class Inner:
        pass


print('__qualname__' in Outer.Inner.__dict__, Outer.Inner.__qualname__)
print(hasattr(Outer.Inner(), '__qualname__'))

# type() created classes too
D = type('D', (), {})
print('__qualname__' in D.__dict__, D.__qualname__, hasattr(D(), '__qualname__'))

# an explicit __qualname__ in the body sets the type's qualname
class E:
    __qualname__ = 'Custom.Name'


print(E.__qualname__, '__qualname__' in E.__dict__)
