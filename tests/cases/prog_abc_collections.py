"""Custom containers built the way real libraries build them: on top of the
collections.abc mixins, abc.ABC with abstract methods, and subclasses of
builtin/collections types. Each probe is independent so that one failure
does not hide the others."""
import abc
import bisect
from collections import Counter, OrderedDict, defaultdict, UserDict
from collections.abc import MutableMapping, MutableSequence, Set, Mapping, Sequence


def check(label, f):
    try:
        print(label, f())
    except Exception as e:
        print(label, "raised", type(e).__name__, e)


class CaseInsensitiveDict(MutableMapping):
    def __init__(self, data=(), **kw):
        self._d = {}
        self.update(data, **kw)

    def __getitem__(self, k):
        return self._d[k.lower()][1]

    def __setitem__(self, k, v):
        self._d[k.lower()] = (k, v)

    def __delitem__(self, k):
        del self._d[k.lower()]

    def __iter__(self):
        return (orig for orig, _ in self._d.values())

    def __len__(self):
        return len(self._d)

    def __repr__(self):
        return "CID(%r)" % dict(self.items())


class SortedList(MutableSequence):
    def __init__(self, items=()):
        self._items = sorted(items)

    def __getitem__(self, i):
        return self._items[i]

    def __setitem__(self, i, v):
        raise TypeError("use add() on a SortedList")

    def __delitem__(self, i):
        del self._items[i]

    def __len__(self):
        return len(self._items)

    def insert(self, i, v):
        self.add(v)

    def add(self, v):
        bisect.insort(self._items, v)

    def __repr__(self):
        return "SortedList(%r)" % self._items


class Bag(Set):
    def __init__(self, items=()):
        self._items = list(dict.fromkeys(items))

    def __contains__(self, x):
        return x in self._items

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        return "Bag(%r)" % sorted(self._items)


class Shape(abc.ABC):
    @abc.abstractmethod
    def area(self):
        ...

    def describe(self):
        return "%s with area %.2f" % (type(self).__name__, self.area())


class Square(Shape):
    def __init__(self, s):
        self.s = s

    def area(self):
        return self.s ** 2


class Tally(Counter):
    def top(self):
        return self.most_common(1)[0][0]


class History(OrderedDict):
    pass


class Config(UserDict):
    def __setitem__(self, k, v):
        super().__setitem__(k.upper(), v)



def section(name):
    """Run a section; an exception escaping it is reported and the next section runs."""
    def deco(fn):
        try:
            fn()
        except Exception as e:
            print(name, "section raised", type(e).__name__, e)
        return fn
    return deco


@section("cid")
def _():
    headers = CaseInsensitiveDict({"Content-Type": "json"}, Accept="*/*")
    check("cid get", lambda: (headers["content-type"], headers.get("ACCEPT"), headers.get("x", 0)))
    check("cid mixins", lambda: ("accept" in headers, len(headers), sorted(headers), headers.pop("accept")))
    check("cid setdefault/update", lambda: (headers.setdefault("X-Id", 7), headers.update(y=1), sorted(headers.keys())))
    check("cid eq", lambda: headers == {"Content-Type": "json", "X-Id": 7, "y": 1})
    check("cid isinstance", lambda: (isinstance(headers, Mapping), isinstance(headers, dict),
                                     issubclass(CaseInsensitiveDict, MutableMapping)))


@section("sorted")
def _():
    sl = SortedList([5, 1, 4])
    check("sorted add", lambda: (sl.add(3), sl.append(0), sl.extend([9, 2]), sl)[3])
    check("sorted mixins", lambda: (sl.index(4), sl.count(9), 4 in sl, list(reversed(sl))[:3], sl[-1], sl[1:3]))
    check("sorted pop/remove", lambda: (sl.pop(), sl.remove(0), sl))
    check("sorted setitem", lambda: sl.__setitem__(0, 1))
    check("sorted isinstance", lambda: (isinstance(sl, Sequence), isinstance(sl, list)))


@section("bag")
def _():
    a, b = Bag("abcd"), Bag("cdef")
    check("bag ops", lambda: (a & b, a | b, a - b, a ^ b))
    check("bag cmp", lambda: (Bag("ab") <= a, a == Bag("dcba"), a.isdisjoint(Bag("xyz")), len(a | b)))


@section("abc")
def _():
    check("abc ok", lambda: Square(3).describe())
    check("abc abstract", lambda: type(Shape()).__name__)
    check("abc isinstance", lambda: (isinstance(Square(1), Shape), issubclass(Square, abc.ABC)))


@section("tally")
def _():
    t = Tally("abracadabra")
    check("tally", lambda: (t.top(), t["a"], t["z"], sorted(t.items())[:2]))
    check("tally repr", lambda: repr(Tally("aab")))
    check("tally add", lambda: sorted((Tally("ab") + Tally("bc")).items()))


@section("history")
def _():
    h = History(a=1)
    h["b"] = 2
    h.move_to_end("a")
    check("history", lambda: (list(h), repr(h)))


@section("userdict")
def _():
    cfg = Config(debug=True)
    cfg["level"] = 3
    check("userdict", lambda: (dict(cfg), "LEVEL" in cfg, cfg.get("DEBUG"), len(cfg)))


@section("defaultdict")
def _():
    dd = defaultdict(list)
    for word in "one two three four five six".split():
        dd[len(word)].append(word)
    check("defaultdict", lambda: (sorted(dd.items()), dd[10], len(dd)))
