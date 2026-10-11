# Assigning a new __dict__ replaces the attribute dictionary of an instance
# or a function.


class A:
    pass


a = A()
a.old = 1
a.__dict__ = {'x': 1}
print(a.x, a.__dict__, hasattr(a, 'old'))
new = {'y': 2}
a.__dict__ = new
a.z = 3
print(new, a.__dict__ is new)
try:
    a.__dict__ = 5
except TypeError as e:
    print('TypeError:', e)


def f():
    pass


f.__dict__ = {'tag': 'v'}
print(f.tag, f.__dict__)
print(A.__dict__['__module__'], type(A.__dict__).__name__)
