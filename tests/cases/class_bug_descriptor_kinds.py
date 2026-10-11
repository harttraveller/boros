# Data descriptors that lack __get__ (only __set__ and/or __delete__).

class SetOnly:
    def __set__(self, obj, value):
        obj.__dict__['seen'] = value


class UsesSetOnly:
    x = SetOnly()


u = UsesSetOnly()
u.x = 5
print(u.seen)
# class access returns the descriptor itself (no __get__)
print(type(UsesSetOnly.x).__name__, UsesSetOnly.__dict__['x'] is UsesSetOnly.x)
# instance access: no __get__, so the instance dict is used if present ...
u.__dict__['x'] = 'dict x'
print(u.x)
# ... otherwise the descriptor object itself is returned
u2 = UsesSetOnly()
print(type(u2.x).__name__)


class DelOnly:
    def __get__(self, obj, owner):
        return 'DelOnly.get'

    def __delete__(self, obj):
        print('DelOnly.delete')


class UsesDelOnly:
    y = DelOnly()


ud = UsesDelOnly()
print(ud.y)
del ud.y
# assignment to a data descriptor without __set__
try:
    ud.y = 3
except AttributeError as e:
    print('AttributeError:', e)

# deleting through a descriptor without __delete__
try:
    del u.x
except AttributeError as e:
    print('AttributeError:', e)
