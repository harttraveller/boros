# dataclasses on interpreted classes.
from dataclasses import dataclass, field, asdict, astuple, replace, fields, is_dataclass


@dataclass
class Point:
    x: int
    y: int = 0

    def norm1(self):
        return abs(self.x) + abs(self.y)


p = Point(1, 2)
print(p, Point(3), p == Point(1, 2), p != Point(2, 2), p.norm1())
print(is_dataclass(Point), [f.name for f in fields(Point)], asdict(p), astuple(p), replace(p, y=9))


@dataclass(order=True, frozen=True)
class Version:
    major: int
    minor: int = 0
    tags: list = field(default_factory=list, compare=False)


print(Version(1, 2) < Version(1, 3), sorted([Version(2), Version(1, 5)]), hash(Version(1)) == hash(Version(1)))
try:
    Version(1).major = 3
except Exception as e:
    print(type(e).__name__, e)


@dataclass
class Point3(Point):
    z: int = 9


print(Point3(1, 2, 3), Point3(1).norm1())
try:
    Point()
except TypeError as e:
    print('TypeError:', e)
