# Assigning function attributes checks the type of the new value.


def f(a=1):
    return a


def attempt(attr, value):
    try:
        setattr(f, attr, value)
        print('set', attr, getattr(f, attr))
    except TypeError as e:
        print('TypeError', attr, '-', e)


attempt('__defaults__', 5)
attempt('__defaults__', [1])
attempt('__kwdefaults__', 5)
attempt('__kwdefaults__', [('a', 1)])
attempt('__name__', 5)
attempt('__name__', None)
attempt('__doc__', 7)
attempt('__defaults__', (3,))
print(f())
attempt('__defaults__', None)
attempt('__kwdefaults__', None)
attempt('__name__', 'g')
try:
    del f.__name__
except TypeError as e:
    print('TypeError del __name__ -', e)
f.__defaults__ = (4,)
del f.__defaults__
print('deleted __defaults__', f.__defaults__)
del f.__doc__
print('deleted __doc__', f.__doc__)
try:
    f.__dict__ = 5
except TypeError as e:
    print('TypeError __dict__ -', e)
