# TypeError messages for unsupported comparisons keep the operator and the
# operand order as written, including when the user object is on the right.
class X:
    pass


for thunk in [lambda: X() < 1, lambda: 1 < X(), lambda: "a" >= X(), lambda: X() >= "a", lambda: None > X(),
              lambda: 1.5 <= X(), lambda: [1] < X(), lambda: X() < X()]:
    try:
        thunk()
    except TypeError as e:
        print("TypeError:", e)
