# Listing the same base class twice is a TypeError with a specific message.

class X:
    pass


class Y(X):
    pass


for bases in [(X, X), (Y, X, Y)]:
    try:
        type('Bad', bases, {})
    except TypeError as e:
        print('TypeError:', e)

try:
    class Bad(X, X):
        pass
except TypeError as e:
    print('TypeError:', e)

# a real MRO conflict keeps its own message
try:
    class Bad2(X, Y):
        pass
except TypeError as e:
    print('TypeError:', e)
