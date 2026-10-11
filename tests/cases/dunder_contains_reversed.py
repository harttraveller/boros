# Membership tests (__contains__ and its fallbacks) and reversed().


class Box:
    def __init__(self, items):
        self.items = items

    def __contains__(self, x):
        print('contains', x)
        return x in self.items


b = Box([1, 2, 3])
print(2 in b, 5 in b, 2 not in b, 5 not in b)


class Truthy:
    def __contains__(self, x):
        return 'yes'   # result converted to bool


class Falsy:
    def __contains__(self, x):
        return []


print(1 in Truthy(), 1 not in Truthy(), 1 in Falsy(), 1 not in Falsy())


# fallback to __iter__
class It:
    def __iter__(self):
        print('iter called')
        return iter([1, 2, 3])


print(2 in It(), 7 in It())


# fallback to __getitem__
class Gi:
    def __getitem__(self, i):
        if i > 3:
            raise IndexError
        return i * i


print(4 in Gi(), 5 in Gi(), 9 not in Gi())


# fallback uses identity then ==
class Eq:
    def __eq__(self, o):
        print('Eq.__eq__')
        return True


e = Eq()
print(e in It(), 'identity:', e in [e])


class NaNLike:
    def __eq__(self, o):
        return False


n = NaNLike()
print(n in [n], n in It() if False else 'skip', n in (NaNLike(),))


# not a container
class Nothing:
    pass


def attempt(label, f):
    try:
        print(label, '->', f())
    except TypeError as ex:
        print(label, '-> TypeError:', ex)


attempt('1 in Nothing()', lambda: 1 in Nothing())
attempt('1 not in Nothing()', lambda: 1 not in Nothing())


class ContainsNone:
    __contains__ = None

    def __iter__(self):
        return iter([1])


attempt('1 in ContainsNone()', lambda: 1 in ContainsNone())


# __contains__ raising propagates
class Raises:
    def __contains__(self, x):
        raise LookupError('nope')


try:
    1 in Raises()
except LookupError as ex:
    print('LookupError:', ex)

# membership in host containers uses the user's __eq__/__hash__
print(Eq() in [1], Eq() in (0,), Eq() in [])


# reversed()
class Rev:
    def __reversed__(self):
        return iter('cba')


class SeqRev:
    def __len__(self):
        return 3

    def __getitem__(self, i):
        print('getitem', i)
        return 'abc'[i]


print(list(reversed(Rev())), list(reversed(SeqRev())))
print(''.join(reversed(SeqRev())))
print(type(reversed(SeqRev())).__name__, type(reversed(Rev())).__name__)


class OnlyLen:
    def __len__(self):
        return 3


class OnlyGetitem:
    def __getitem__(self, i):
        return i


class RevNone:
    __reversed__ = None

    def __len__(self):
        return 1

    def __getitem__(self, i):
        return i


attempt('reversed(Nothing())', lambda: reversed(Nothing()))
attempt('reversed(OnlyLen())', lambda: reversed(OnlyLen()))
attempt('reversed(OnlyGetitem())', lambda: reversed(OnlyGetitem()))
attempt('reversed(RevNone())', lambda: list(reversed(RevNone())))


class RevReturnsList:
    def __reversed__(self):
        return [3, 2, 1]


r = reversed(RevReturnsList())
print(type(r).__name__, r)


# reversed of a sequence whose __len__ shrinks: IndexError ends iteration
class Shrink:
    def __len__(self):
        return 4

    def __getitem__(self, i):
        if i >= 2:
            raise IndexError(i)
        return i


try:
    print(list(reversed(Shrink())))
except IndexError as ex:
    print('IndexError', ex)
