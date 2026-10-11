# Sequence concat/repeat where the right operand is a user object: after the
# right operand's reflected method fails, CPython falls back to the left
# builtin sequence's concat/repeat (which accepts subclasses of that builtin).
class L(list):
    pass


class S(str):
    pass


class T(tuple):
    pass


class I(int):
    pass


r = [1] + L([2])
print(r, type(r).__name__)
r = "a" + S("b")
print(r, type(r).__name__)
r = (1,) + T((2,))
print(r, type(r).__name__)
print([1] * I(2), "ab" * I(2), (0,) * I(3), I(2) * [7], b"x" * I(3))
acc = [0]
acc += L([1])
print(acc, type(acc).__name__)


class V:
    def __radd__(self, o):
        return NotImplemented

    def __rmul__(self, o):
        return NotImplemented


for thunk in [lambda: "s" + V(), lambda: [1] + V(), lambda: (1,) + V(), lambda: b"x" + V(), lambda: [1] * V(),
              lambda: "s" * V()]:
    try:
        thunk()
    except TypeError as e:
        print("TypeError:", e)


class Ix:
    def __index__(self):
        return 3


print([1] * Ix(), "ab" * Ix(), Ix() * (0,), b"-" * Ix())
