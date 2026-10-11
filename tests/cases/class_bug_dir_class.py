# dir() of a class and an instance include __dict__ and __weakref__ for
# ordinary classes (they come from the class's own __dict__).

class Point:
    def __init__(self):
        self.x = 1


class Sub(Point):
    pass


class Slotted:
    __slots__ = ('a',)


for obj in (Point, Point(), Sub, Sub(), Slotted, Slotted()):
    names = dir(obj)
    print('__dict__' in names, '__weakref__' in names, '__init__' in names, '__module__' in names)
print([n for n in dir(Point()) if not n.startswith('__')])
