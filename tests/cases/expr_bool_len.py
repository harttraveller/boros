# Truth testing through __len__ validates the result like len() does.
class BadLen:
    def __init__(self, r):
        self.r = r

    def __len__(self):
        return self.r


for r in [-1, "x", 2.0, None, 0, 3, True]:
    for name, thunk in [("bool", lambda: bool(BadLen(r))), ("not", lambda: not BadLen(r)),
                        ("if", lambda: "yes" if BadLen(r) else "no"), ("len", lambda: len(BadLen(r)))]:
        try:
            print(repr(r), name, thunk())
        except (ValueError, TypeError) as e:
            print(repr(r), name, type(e).__name__ + ":", e)
