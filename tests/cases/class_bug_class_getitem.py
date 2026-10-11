# Subscripting a class calls __class_getitem__; otherwise it is an error.

class Box:
    def __class_getitem__(cls, item):
        return '%s[%s]' % (cls.__name__, getattr(item, '__name__', item))


class SubBox(Box):
    pass


print(Box[int], Box['x'], SubBox[str], Box[int, str] if False else Box[(1, 2)])


class Plain:
    def __getitem__(self, k):      # instance subscription only
        return k * 2


print(Plain()[4])
try:
    Plain[1]
except TypeError as e:
    print('TypeError:', e)

# builtin generic aliases still work
print(list[int], dict[str, int])
