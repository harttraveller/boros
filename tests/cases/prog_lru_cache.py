"""LRU caches: a hand-written doubly linked list cache implementing the
mapping protocol, an OrderedDict-based subclass of dict, a memoizing
decorator with stats, and functools.lru_cache for comparison."""
import functools
from collections import OrderedDict


class _Node:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value
        self.prev = self.next = None


class LRUCache:
    def __init__(self, capacity, on_evict=None):
        if capacity <= 0:
            raise ValueError("capacity must be positive, got %r" % (capacity,))
        self.capacity = capacity
        self.map = {}
        self.head = _Node()
        self.tail = _Node()
        self.head.next = self.tail
        self.tail.prev = self.head
        self.on_evict = on_evict
        self.hits = self.misses = 0

    def _unlink(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _push_front(self, node):
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def __getitem__(self, key):
        node = self.map.get(key)
        if node is None:
            self.misses += 1
            raise KeyError(key)
        self.hits += 1
        self._unlink(node)
        self._push_front(node)
        return node.value

    def __setitem__(self, key, value):
        node = self.map.get(key)
        if node is not None:
            node.value = value
            self._unlink(node)
            self._push_front(node)
            return
        if len(self.map) >= self.capacity:
            lru = self.tail.prev
            self._unlink(lru)
            del self.map[lru.key]
            if self.on_evict:
                self.on_evict(lru.key, lru.value)
        node = _Node(key, value)
        self.map[key] = node
        self._push_front(node)

    def __delitem__(self, key):
        node = self.map.pop(key)
        self._unlink(node)

    def keys_mru(self):
        node = self.head.next
        while node is not self.tail:
            yield node.key
            node = node.next

    def __iter__(self):
        # snapshot: reading items through __getitem__ reorders the list
        return iter(list(self.keys_mru()))

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    _marker = object()

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def pop(self, key, default=_marker):
        try:
            value = self.map[key].value
        except KeyError:
            if default is self._marker:
                raise
            return default
        del self[key]
        return value

    def update(self, other=(), **kw):
        items = other.items() if hasattr(other, "items") else other
        for k, v in list(items) + list(kw.items()):
            self[k] = v

    def keys(self):
        return list(self)

    def values(self):
        return [self.map[k].value for k in self]

    def items(self):
        return [(k, self.map[k].value) for k in self]

    def clear(self):
        for k in list(self):
            del self[k]

    def __eq__(self, other):
        if isinstance(other, LRUCache):
            other = dict(other.items())
        if not isinstance(other, dict):
            return NotImplemented
        return dict(self.items()) == other

    __hash__ = None

    def __repr__(self):
        return "LRUCache(%d, [%s])" % (self.capacity, ", ".join("%r: %r" % (k, self.map[k].value) for k in self))


class OrderedLRU(OrderedDict):
    def __init__(self, maxsize=3, *args, **kwds):
        self.maxsize = maxsize
        super().__init__(*args, **kwds)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]


def memoize(maxsize=128):
    def deco(fn):
        cache = LRUCache(maxsize)

        @functools.wraps(fn)
        def wrapper(*args, **kw):
            key = (args, tuple(sorted(kw.items())))
            try:
                return cache[key]
            except KeyError:
                pass
            result = fn(*args, **kw)
            cache[key] = result
            return result

        wrapper.cache = cache
        wrapper.cache_info = lambda: (cache.hits, cache.misses, len(cache))
        return wrapper
    return deco


evicted = []
c = LRUCache(3, on_evict=lambda k, v: evicted.append((k, v)))
for k, v in [("a", 1), ("b", 2), ("c", 3)]:
    c[k] = v
_ = c["a"]
c["d"] = 4
c["b" if "b" in c else "c"] = 30
c["e"] = 5
print(c, evicted, len(c), list(c), "a" in c, "b" in c)
print(c.get("zz", "default"), c.get("a"), c.setdefault("f", 6), dict(c.items()), c.hits, c.misses)
c.update({"g": 7}, h=8)
print(sorted(c.keys()), list(c.values()), c.pop("h"), c.pop("nope", None), evicted[-3:])
try:
    c["missing"]
except KeyError as e:
    print("KeyError", e)
try:
    LRUCache(0)
except ValueError as e:
    print("ValueError", e)
del c["g"]
print(c == {"f": 6}, c, c == {"f": 6, "c": 30}, {"c": 30, "f": 6} == c, issubclass(LRUCache, dict))
c.clear()
print(len(c), repr(c))

o = OrderedLRU(2)
o["x"] = 1
o["y"] = 2
o["x"]
o["z"] = 3
print(o, list(o.items()), isinstance(o, dict), o.maxsize)


@memoize(maxsize=64)
def fib(n):
    """Naive fibonacci, made fast by the cache."""
    return n if n < 2 else fib(n - 1) + fib(n - 2)


@functools.lru_cache(maxsize=None)
def fib2(n):
    return n if n < 2 else fib2(n - 1) + fib2(n - 2)


print(fib(80), fib.__name__, fib.__doc__, fib.cache_info(), fib.__wrapped__.__name__)
print(fib2(80), fib2.cache_info(), fib2.__name__)
fib2.cache_clear()
print(fib2.cache_info())


@memoize()
def grid_paths(r, c, *, blocked=frozenset()):
    if (r, c) in blocked:
        return 0
    if r == 0 or c == 0:
        return 1
    return grid_paths(r - 1, c, blocked=blocked) + grid_paths(r, c - 1, blocked=blocked)


print(grid_paths(10, 10), grid_paths(6, 6, blocked=frozenset({(3, 3), (2, 4)})), grid_paths.cache_info())
