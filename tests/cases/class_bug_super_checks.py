# super(type, obj) validates its arguments and exposes __thisclass__,
# __self__ and __self_class__.

class Base:
    def m(self):
        return 'Base.m'


class Child(Base):
    def m(self):
        return 'Child.m'


class Unrelated:
    pass


c = Child()
s = super(Child, c)
print(s.m(), s.__thisclass__.__name__, s.__self__ is c, s.__self_class__.__name__)
sc = super(Child, Child)
print(sc.__thisclass__.__name__, sc.__self__ is Child, sc.__self_class__.__name__)

for args in [(Child, 5), (Child, Unrelated()), (Child, Base()), (Child, Base), (5, c)]:
    try:
        super(*args)
        print('no error for', [type(a).__name__ for a in args])
    except TypeError as e:
        print('TypeError:', e)

# unbound super object
u = super(Child)
print(u.__thisclass__.__name__, u.__self__, u.__self_class__)
