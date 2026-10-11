"""A Matrix class with full operator overloading (arithmetic, reflected and
in-place operators, @, ==, hashing of frozen matrices, indexing with tuples
and slices, iteration, bool, abs, neg), Fraction entries for exact Gaussian
elimination, and a Vector subclass."""
from fractions import Fraction
from numbers import Number
import math


class MatrixError(ValueError):
    pass


class Matrix:
    __array_priority__ = 1

    def __init__(self, rows):
        rows = [list(r) for r in rows]
        if not rows or any(len(r) != len(rows[0]) for r in rows):
            raise MatrixError("rows must be non-empty and of equal length")
        self.rows = rows

    @classmethod
    def identity(cls, n):
        return cls([[int(i == j) for j in range(n)] for i in range(n)])

    @classmethod
    def zeros(cls, r, c):
        return cls([[0] * c for _ in range(r)])

    @property
    def shape(self):
        return len(self.rows), len(self.rows[0])

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.rows)

    def __str__(self):
        cells = [[str(x) for x in r] for r in self.rows]
        w = max(len(c) for r in cells for c in r)
        return "\n".join("[" + " ".join(c.rjust(w) for c in r) + "]" for r in cells)

    def __getitem__(self, idx):
        if isinstance(idx, tuple):
            i, j = idx
            if isinstance(i, slice) or isinstance(j, slice):
                rows = self.rows[i] if isinstance(i, slice) else [self.rows[i]]
                return Matrix([r[j] if isinstance(j, slice) else [r[j]] for r in rows])
            return self.rows[i][j]
        return Vector(self.rows[idx])

    def __setitem__(self, idx, value):
        i, j = idx
        self.rows[i][j] = value

    def __iter__(self):
        return (Vector(r) for r in self.rows)

    def __len__(self):
        return len(self.rows)

    def __eq__(self, other):
        if isinstance(other, Matrix):
            return self.rows == other.rows
        return NotImplemented

    def __hash__(self):
        return hash(tuple(map(tuple, self.rows)))

    def __bool__(self):
        return any(x for r in self.rows for x in r)

    def _elementwise(self, other, op):
        if isinstance(other, Matrix):
            if self.shape != other.shape:
                raise MatrixError("shape mismatch %s vs %s" % (self.shape, other.shape))
            return Matrix([[op(a, b) for a, b in zip(r1, r2)] for r1, r2 in zip(self.rows, other.rows)])
        if isinstance(other, Number):
            return Matrix([[op(a, other) for a in r] for r in self.rows])
        return NotImplemented

    def __add__(self, other):
        return self._elementwise(other, lambda a, b: a + b)

    __radd__ = __add__

    def __sub__(self, other):
        return self._elementwise(other, lambda a, b: a - b)

    def __rsub__(self, other):
        return self._elementwise(other, lambda a, b: b - a)

    def __mul__(self, other):
        return self._elementwise(other, lambda a, b: a * b)

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, k):
        if not isinstance(k, Number):
            return NotImplemented
        return Matrix([[Fraction(a) / k for a in r] for r in self.rows])

    def __matmul__(self, other):
        if not isinstance(other, Matrix):
            return NotImplemented
        (n, m), (m2, p) = self.shape, other.shape
        if m != m2:
            raise MatrixError("cannot multiply %dx%d by %dx%d" % (n, m, m2, p))
        cols = list(zip(*other.rows))
        return Matrix([[sum(a * b for a, b in zip(r, c)) for c in cols] for r in self.rows])

    def __pow__(self, k):
        if k < 0:
            return self.inverse() ** -k
        result = Matrix.identity(self.shape[0])
        base = self
        while k:
            if k & 1:
                result = result @ base
            base = base @ base
            k >>= 1
        return result

    def __neg__(self):
        return self * -1

    def __pos__(self):
        return self

    def __abs__(self):
        return Matrix([[abs(x) for x in r] for r in self.rows])

    def __iadd__(self, other):
        r = self + other
        self.rows = r.rows
        return self

    def T(self):
        return Matrix(zip(*self.rows))

    def det(self):
        n, m = self.shape
        if n != m:
            raise MatrixError("determinant needs a square matrix")
        a = [[Fraction(x) for x in r] for r in self.rows]
        d = Fraction(1)
        for c in range(n):
            p = next((r for r in range(c, n) if a[r][c] != 0), None)
            if p is None:
                return Fraction(0)
            if p != c:
                a[c], a[p] = a[p], a[c]
                d = -d
            d *= a[c][c]
            for r in range(c + 1, n):
                f = a[r][c] / a[c][c]
                for k in range(c, n):
                    a[r][k] -= f * a[c][k]
        return d

    def inverse(self):
        n = self.shape[0]
        if self.det() == 0:
            raise ZeroDivisionError("matrix is singular")
        a = [[Fraction(x) for x in r] + [Fraction(int(i == j)) for j in range(n)] for i, r in enumerate(self.rows)]
        for c in range(n):
            p = max(range(c, n), key=lambda r: abs(a[r][c]))
            a[c], a[p] = a[p], a[c]
            pv = a[c][c]
            a[c] = [x / pv for x in a[c]]
            for r in range(n):
                if r != c and a[r][c]:
                    f = a[r][c]
                    a[r] = [x - f * y for x, y in zip(a[r], a[c])]
        return Matrix([r[n:] for r in a])


class Vector(Matrix):
    def __init__(self, values):
        super().__init__([values])

    def __repr__(self):
        return "Vector(%r)" % self.rows[0]

    def __matmul__(self, other):
        if isinstance(other, Vector):
            return sum(a * b for a, b in zip(self.rows[0], other.rows[0]))
        return super().__matmul__(other)

    def __abs__(self):
        return math.sqrt(self @ self)

    def __iter__(self):
        return iter(self.rows[0])

    def __getitem__(self, i):
        return self.rows[0][i]


A = Matrix([[2, 1], [1, 3]])
B = Matrix([[1, 2], [3, 4]])
I = Matrix.identity(2)
print(A + B, A - 1, 10 - A, 2 * A, A * 0.5, sep="\n")
print(repr(A @ B), A @ I == A, A == B, A != B, A == [[2, 1], [1, 3]])
print(A ** 5, B.det(), A.det(), (A @ A.inverse()) == I)
print(A.inverse(), B ** -1, sep="\n")
print(repr(B / 2), -B, abs(-B) == B, +A is A, bool(Matrix.zeros(2, 2)), bool(A))
M = Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 10]])
print(M[0], M[1, 2], repr(M[0:2, 1:]), repr(M[:, 0]), M.shape, len(M), M.T().shape)
print(M.det(), M.inverse() @ M == Matrix.identity(3), [list(r) for r in M][2])
M[2, 2] = 9
print(M.det())
try:
    M.inverse()
except ZeroDivisionError as e:
    print("ZeroDivisionError:", e)
C = A
C += 1
print(C is A, A)
v, w = Vector([3, 4]), Vector([1, 2])
print(abs(v), v @ w, repr(v + w), list(v * 2), sum(v), v[1], isinstance(v, Matrix), repr(w @ Matrix([[1], [1]])))
print(len({A, Matrix([[3, 2], [2, 4]]), B}), sorted([3, 1, 2], key=lambda k: Matrix.identity(k).det()))
for bad in (lambda: A + Matrix([[1, 2, 3]]), lambda: A @ Matrix([[1, 2, 3]]), lambda: Matrix([[1], [1, 2]]),
            lambda: A @ 3, lambda: "x" + A, lambda: A / "y", lambda: M[5], lambda: Matrix([[1, 2]]).det()):
    try:
        bad()
    except (MatrixError, TypeError, IndexError) as e:
        print(type(e).__name__ + ":", e)
print(issubclass(MatrixError, ValueError), Fraction(1, 3) + Matrix.identity(1), Matrix([[Fraction(1, 2)]]) * 4)
