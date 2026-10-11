"""Order processing workflow driven by enum states: Enum with values and
methods, IntEnum priorities, Flag permissions with auto(), lookup by value
and by name, iteration, and a transition table keyed by enum members."""
from enum import Enum, IntEnum, Flag, auto


class State(Enum):
    NEW = "new"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    @property
    def final(self):
        return self in (State.DELIVERED, State.CANCELLED)

    def __str__(self):
        return self.value.upper()


class Priority(IntEnum):
    LOW = 1
    NORMAL = 2
    HIGH = 3


class Perm(Flag):
    READ = auto()
    WRITE = auto()
    SHIP = auto()
    ADMIN = READ | WRITE | SHIP


TRANSITIONS = {
    State.NEW: {State.PAID, State.CANCELLED},
    State.PAID: {State.SHIPPED, State.CANCELLED},
    State.SHIPPED: {State.DELIVERED},
}


class TransitionError(Exception):
    pass


class Order:
    def __init__(self, oid, priority=Priority.NORMAL):
        self.oid = oid
        self.state = State.NEW
        self.priority = Priority(priority)
        self.log = [self.state]

    def advance(self, new, perms):
        if new is State.SHIPPED and Perm.SHIP not in perms:
            raise PermissionError("order %d: missing %s" % (self.oid, Perm.SHIP))
        if new not in TRANSITIONS.get(self.state, ()):
            raise TransitionError("order %d: %s -> %s not allowed" % (self.oid, self.state, new))
        self.state = new
        self.log.append(new)


orders = [Order(1), Order(2, Priority.HIGH), Order(3, 1)]
script = [(1, "paid", Perm.WRITE), (1, "shipped", Perm.WRITE), (1, "shipped", Perm.ADMIN),
          (2, "cancelled", Perm.READ | Perm.WRITE), (2, "paid", Perm.ADMIN), (3, "delivered", Perm.ADMIN),
          (1, "delivered", Perm.ADMIN), (3, "teleported", Perm.ADMIN)]
for oid, state_name, perms in script:
    order = orders[oid - 1]
    try:
        order.advance(State(state_name), perms)
        print("order", oid, "->", order.state, "final" if order.state.final else "")
    except (TransitionError, PermissionError, ValueError) as e:
        print(type(e).__name__ + ":", e)
for o in sorted(orders, key=lambda o: (-o.priority, o.oid)):
    print(o.oid, o.priority.name, int(o.priority), [s.name for s in o.log])
print(list(State)[:2], State["PAID"], State.PAID.value, repr(State.NEW), len(State), State.NEW in State)
print(Priority.HIGH > Priority.LOW, Priority.HIGH + 1, sorted([Priority.HIGH, Priority.LOW]), max(Priority).name)
print(Perm.ADMIN, Perm.READ in Perm.ADMIN, Perm.READ | Perm.SHIP, bool(Perm.READ & Perm.WRITE), Perm(3))
print({s: s.final for s in State}, State.NEW is State("new"), isinstance(State.NEW, State), type(State.PAID).__name__)
