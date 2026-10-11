# More enum features: custom methods, __str__, properties, _missing_,
# tuple values with __init__, str mixin, StrEnum, unique, classmethods.
from enum import Enum, StrEnum, IntFlag, unique, auto


class Planet(Enum):
    MERCURY = (3.303e+23, 2.4397e6)
    EARTH = (5.976e+24, 6.37814e6)

    def __init__(self, mass, radius):
        self.mass = mass
        self.radius = radius

    @property
    def surface_gravity(self):
        return round(6.673e-11 * self.mass / (self.radius * self.radius), 2)

    def __str__(self):
        return 'Planet ' + self.name.title()


print(Planet.EARTH.surface_gravity, str(Planet.MERCURY), Planet.EARTH.value[1])


class Shape(Enum):
    SQUARE = 'sq'
    CIRCLE = 'ci'

    @classmethod
    def _missing_(cls, value):
        for m in cls:
            if m.value == str(value).lower()[:2]:
                return m
        return None

    @classmethod
    def names(cls):
        return [m.name for m in cls]

    def describe(self):
        return '%s/%s' % (self.name, super().__str__())


print(Shape('SQuare'), Shape.names(), Shape.CIRCLE.describe())
try:
    Shape('triangle')
except ValueError as e:
    print('ValueError:', e)


class Mode(str, Enum):
    READ = 'r'
    WRITE = 'w'


print(Mode.READ == 'r', Mode('w'), Mode.READ.upper(), isinstance(Mode.READ, str))


class Level(StrEnum):
    LOW = auto()
    HIGH = auto()


print(Level.LOW, Level.HIGH == 'high', list(Level))


class Perm(IntFlag):
    R = 4
    W = 2
    X = 1


print(Perm.R | Perm.X, int(Perm.R | Perm.W), Perm(7))

try:
    @unique
    class Dup(Enum):
        A = 1
        B = 1
except ValueError as e:
    print('ValueError:', e)

print(Shape.SQUARE.__class__ is Shape, type(Shape).__name__, Shape.__members__.keys())
