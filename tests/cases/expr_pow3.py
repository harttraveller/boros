# Three-argument pow() with user objects (no __rpow__ fallback in 3.13).
class X:
    def __rpow__(self, o, mod=None):
        return "rpow"


class I(int):
    pass


for thunk in [lambda: pow(2, X(), 5), lambda: pow(2, 3, X())]:
    try:
        print(thunk())
    except TypeError as e:
        print("TypeError:", e)
print(pow(2, I(10), 1000), pow(I(3), 4, 5), pow(2, 5, I(7)), 2 ** X())
