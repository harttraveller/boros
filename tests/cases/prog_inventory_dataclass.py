"""Warehouse inventory built on dataclasses: defaults, default_factory,
field(compare=False), order=True sorting, frozen value objects used as
dict keys, __post_init__ validation, replace(), asdict()/astuple(), and
inheritance between dataclasses."""
from dataclasses import dataclass, field, asdict, astuple, replace, fields, FrozenInstanceError
from decimal import Decimal


@dataclass(frozen=True, order=True)
class Location:
    aisle: str
    shelf: int

    def __str__(self):
        return "%s-%02d" % (self.aisle, self.shelf)


@dataclass(order=True)
class Item:
    sku: str
    price: Decimal = field(compare=False)
    qty: int = field(default=0, compare=False)
    tags: list = field(default_factory=list, compare=False, repr=False)

    def __post_init__(self):
        if self.qty < 0:
            raise ValueError("negative quantity for %s" % self.sku)
        self.price = Decimal(self.price)

    @property
    def value(self):
        return self.price * self.qty


@dataclass
class Perishable(Item):
    days_left: int = 7

    def expired(self):
        return self.days_left <= 0


class Warehouse:
    def __init__(self):
        self.stock = {}

    def put(self, loc, item):
        self.stock.setdefault(loc, []).append(item)

    def total(self):
        return sum((i.value for items in self.stock.values() for i in items), Decimal(0))

    def report(self):
        for loc in sorted(self.stock):
            items = sorted(self.stock[loc], key=lambda i: i.sku)
            print(" ", loc, [i.sku for i in items], sum(i.qty for i in items))


wh = Warehouse()
wh.put(Location("B", 2), Item("bolt", "0.10", 500, ["metal"]))
wh.put(Location("A", 1), Item("nut", "0.05", 800))
wh.put(Location("B", 2), Perishable("glue", "3.50", 10, days_left=0))
wh.put(Location("A", 1), Item("anchor", "1.25", 40))
print(Item("x", 1, 2))
print(Perishable("milk", "1.20", 3))
wh.report()
print("total value", wh.total())
print(sorted(wh.stock), Location("A", 1) < Location("A", 2), Location("A", 1) == Location("A", 1))
print(hash(Location("C", 3)) == hash(Location("C", 3)), {Location("C", 3): "x"}[Location("C", 3)])
glue = wh.stock[Location("B", 2)][1]
print(glue.expired(), isinstance(glue, Item), asdict(glue), astuple(Location("Z", 9)))
print(replace(glue, qty=1, days_left=5), [f.name for f in fields(Perishable)])
try:
    Item("bad", 1, -1)
except ValueError as e:
    print("ValueError:", e)
try:
    Location("A", 1).shelf = 3
except FrozenInstanceError as e:
    print("FrozenInstanceError:", e)
try:
    Item("x", 1) < Location("A", 1)
except TypeError as e:
    print("TypeError:", e)
print(Item("a", 1) == Item("a", 2, 5), Item("a", 1) == "a", Item.__eq__ is not object.__eq__)
