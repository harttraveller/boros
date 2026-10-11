# functools.total_ordering fills in the missing comparison methods of an
# interpreted class.
import functools


@functools.total_ordering
class V:
    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return self.v == o.v

    def __lt__(self, o):
        return self.v < o.v


print(V(1) < V(2), V(1) <= V(2), V(3) >= V(2), V(1) > V(2), V(2) <= V(2))
print(sorted([V(3), V(1), V(2)], key=lambda x: x)[0].v)
