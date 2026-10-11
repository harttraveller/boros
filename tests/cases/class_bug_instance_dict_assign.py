# Assigning obj.__dict__ replaces the instance namespace.

class P:
    def __init__(self):
        self.a = 1


p = P()
p.__dict__ = {'b': 2}
print(p.b, hasattr(p, 'a'), vars(p), p.__dict__ is vars(p))
new = {'c': 3}
p.__dict__ = new
p.d = 4
print(new, sorted(vars(p)))
try:
    p.__dict__ = [1, 2]
except TypeError as e:
    print('TypeError:', e)

# __class__ assignment error message
try:
    p.__class__ = 5
except TypeError as e:
    print('TypeError:', e)
