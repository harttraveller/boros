# `in` on an object without __contains__/__iter__/__getitem__.
class X:
    pass


for thunk in [lambda: 1 in X(), lambda: 1 not in X(), lambda: 1 in 5, lambda: "a" in None]:
    try:
        thunk()
    except TypeError as e:
        print("TypeError:", e)


class G:
    def __getitem__(self, i):
        if i > 2:
            raise IndexError
        return i


class It:
    def __iter__(self):
        return iter("abc")


print(2 in G(), 5 in G(), "b" in It(), "z" not in It())
