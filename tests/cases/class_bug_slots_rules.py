# __slots__ details: member descriptors, read-only class attributes on
# slotted instances, and conflicts between slots and class variables.

class P:
    __slots__ = ('x',)
    kind = 'shared'

    def method(self):
        return 'm'


print(type(P.__dict__['x']).__name__, type(P.x).__name__)
p = P()
for name, value in [('kind', 'mine'), ('method', None)]:
    try:
        setattr(p, name, value)
        print('set', name, 'ok ->', getattr(p, name))
    except AttributeError as e:
        print('AttributeError:', e)
print(p.kind, P.kind)
try:
    del p.kind
except AttributeError as e:
    print('AttributeError:', e)

try:
    class Conflict:
        __slots__ = ('x',)
        x = 1
except ValueError as e:
    print('ValueError:', e)
