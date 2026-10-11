import functools


# total_ordering on an interpreted class
@functools.total_ordering
class Ver:
    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return self.v == o.v

    def __lt__(self, o):
        return self.v < o.v

    def __repr__(self):
        return 'Ver(%d)' % self.v


try:
    print(Ver(1) <= Ver(2), Ver(3) >= Ver(2), Ver(2) > Ver(1), sorted([Ver(3), Ver(1)]))
except TypeError as e:
    print('total_ordering TypeError:', e)
