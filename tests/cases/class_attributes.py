# Class attributes vs instance attributes.

class Config:
    color = 'red'
    items = []
    count = 0

    def __init__(self, name):
        self.name = name

    def bump(self):
        self.count += 1          # creates an instance attribute
        return self.count

    def add(self, x):
        self.items.append(x)     # mutates the shared class attribute


a = Config('a')
b = Config('b')
print(a.color, b.color, Config.color)
a.color = 'blue'                 # shadow on instance
print(a.color, b.color, Config.color)
Config.color = 'green'           # class change seen by b, not a
print(a.color, b.color, Config.color)
del a.color                      # unshadow
print(a.color)

print(a.bump(), a.bump(), b.bump(), Config.count)
print('count' in a.__dict__, 'count' in Config.__dict__)

a.add(1)
b.add(2)
print(a.items, b.items, Config.items, a.items is Config.items)

# rebinding the list on the instance breaks sharing
a.items = ['own']
a.add(3)
print(a.items, b.items)

# deleting an attribute that exists only on the class via the instance
try:
    del b.color
except AttributeError as e:
    print('AttributeError:', e)

# deleting a class attribute
del Config.count
print(hasattr(Config, 'count'), a.count, hasattr(b, 'count'))
try:
    del Config.nothing
except AttributeError as e:
    print('AttributeError:', e)

# accessing missing attributes
try:
    a.missing
except AttributeError as e:
    print('AttributeError:', e)
try:
    Config.missing
except AttributeError as e:
    print('AttributeError:', e)

# class body can reference earlier class attributes but methods cannot see
# them as bare names
class Scope:
    x = 10
    y = x * 2
    z = [x for _ in range(1)] if False else None

    def method(self):
        try:
            return x
        except NameError as e:
            return 'NameError: ' + str(e)


print(Scope.y, Scope().method())

x = 'global x'
class Scope2:
    x = 'class x'
    def m(self):
        return x
print(Scope2().m())

# class attributes can be functions added later, become methods
def describe(self):
    return 'I am ' + self.name

Config.describe = describe
print(a.describe(), b.describe())

# assigning a function to an instance does not bind it
a.fn = lambda: 'plain function'
print(a.fn())

# instance attribute that shadows a method
b.describe = 'shadowed'
print(b.describe, a.describe())

# class attribute counter via class name
class Tracker:
    instances = 0

    def __init__(self):
        Tracker.instances += 1
        type(self).instances_type = Tracker.instances


Tracker(); Tracker(); t = Tracker()
print(Tracker.instances, t.instances, t.instances_type)

# nested classes
class Outer:
    class Inner:
        value = 42

        class Deeper:
            pass

    def make(self):
        return self.Inner()


print(Outer.Inner.value, Outer().make().value, Outer.Inner.__qualname__, Outer.Inner.Deeper.__qualname__)
print(Outer.Inner.__name__)

# class body executes statements in order, including loops and conditionals
class Body:
    total = 0
    for i in range(4):
        total += i
    if total > 5:
        big = True
    else:
        big = False
    del i


print(Body.total, Body.big, hasattr(Body, 'i'))
