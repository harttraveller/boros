# Variable annotations in a class body populate __annotations__.

class A:
    x: int = 1
    y: str
    z: 'list[int]' = []
    __private: float = 0.5


print(A.__annotations__)
print(A.x, hasattr(A, 'y'), A.z, '__annotations__' in A.__dict__)


class B(A):
    w: bytes


print(B.__annotations__, B.x)


class NoAnn:
    v = 1


print(NoAnn.__dict__.get('__annotations__', 'absent'))

# annotations are evaluated in the class namespace, after the value
class C:
    T = int
    a: T = 5


print(C.__annotations__, C.a)
