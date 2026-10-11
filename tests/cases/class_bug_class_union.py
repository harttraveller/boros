# X | Y with interpreted classes builds a union usable by isinstance.

class A:
    pass


class B(A):
    pass


class C:
    pass


u = A | C
print(u, type(u).__name__)
print(isinstance(B(), u), isinstance(C(), u), isinstance(3, u))
print(isinstance(B(), int | A), isinstance(None, A | None), A | None)
print(issubclass(B, C | A), issubclass(int, A | C), issubclass(B, int | str))
print((A | C) == (A | C), (A | C).__args__ == (A, C))
