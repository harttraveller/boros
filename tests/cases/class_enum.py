# enum.Enum / IntEnum / Flag subclasses defined by the program.
from enum import Enum, IntEnum, Flag, auto


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

    def describe(self):
        return 'color %s=%d' % (self.name, self.value)


print(Color.RED, repr(Color.GREEN), Color.RED.name, Color.RED.value, Color(2), Color['BLUE'])
print(list(Color), len(Color), Color.RED is Color(1), isinstance(Color.RED, Color), type(Color.RED).__name__)
print(Color.RED == 1, Color.BLUE.describe(), [c.name for c in Color])
try:
    Color(7)
except ValueError as e:
    print('ValueError:', e)


class Prio(IntEnum):
    LOW = auto()
    HIGH = auto()


print(Prio.LOW < Prio.HIGH, Prio.HIGH + 1, int(Prio.LOW), sorted([Prio.HIGH, Prio.LOW]))


class Perm(Flag):
    R = 4
    W = 2
    X = 1


print(Perm.R | Perm.W, Perm.R in (Perm.R | Perm.X), bool(Perm.W & Perm.X))
