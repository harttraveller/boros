# sys.exc_info() / sys.exception() inside and outside handlers.
import sys


class Custom(Exception):
    pass


print(sys.exc_info(), sys.exception())

try:
    raise ValueError('host type')
except ValueError:
    t, v, tb = sys.exc_info()
    print(t.__name__, v, tb is not None, sys.exception() is v)

try:
    raise Custom('interp type')
except Custom as c:
    t, v, tb = sys.exc_info()
    print(t.__name__, v, v is c, t is Custom, isinstance(v, Custom))
    print(sys.exception() is c, type(sys.exception()).__name__)

print(sys.exc_info(), sys.exception())


def inner():
    return sys.exc_info()[0]


try:
    raise KeyError
except KeyError:
    print('in called function:', inner().__name__)

# nested handlers restore the outer exception afterwards
try:
    raise Custom('outer')
except Custom:
    try:
        raise IndexError('inner')
    except IndexError:
        print('inner:', type(sys.exception()).__name__)
    print('restored:', type(sys.exception()).__name__, sys.exception())
