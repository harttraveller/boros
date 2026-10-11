"""A program that ends with an uncaught exception raised deep inside a
chain of generators (yield from) while being consumed by a for loop."""


def leaf(items):
    for x in items:
        if x < 0:
            raise ValueError('negative value: %d' % x)
        yield x * 2


def middle(items):
    total = yield from leaf(items)
    yield total


def top():
    for chunk in ([1, 2], [3, -4, 5]):
        yield from middle(chunk)


for v in top():
    print('got', v)
print('not reached')
