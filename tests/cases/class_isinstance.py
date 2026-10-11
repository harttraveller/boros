# isinstance / issubclass with user classes, tuples and builtins.

class Animal: pass
class Dog(Animal): pass
class Cat(Animal): pass
class Puppy(Dog): pass
class Robot: pass


d = Puppy()
print(isinstance(d, Puppy), isinstance(d, Dog), isinstance(d, Animal), isinstance(d, object))
print(isinstance(d, Cat), isinstance(d, (Cat, Robot)), isinstance(d, (Cat, Dog)))
print(isinstance(d, ()), isinstance(d, (Robot, (Cat, (Animal,)))))
print(issubclass(Puppy, Animal), issubclass(Puppy, (Cat, Robot)), issubclass(Puppy, (Robot, Dog)))
print(issubclass(Puppy, Puppy), issubclass(Animal, Puppy), issubclass(Puppy, object))
print(issubclass(Dog, ()), issubclass(Dog, (Robot, (int, Animal))))

# builtins
print(isinstance(1, int), isinstance(True, int), isinstance(1, (str, float)), isinstance(1.0, (str, float)))
print(issubclass(bool, int), issubclass(int, bool), issubclass(int, object), issubclass(list, (dict, list)))
print(isinstance(Dog, type), isinstance(int, type), isinstance(Dog(), type))
print(issubclass(type, object), isinstance(type, type), isinstance(object, type))
print(isinstance(Dog, object), isinstance(len, object))
print(isinstance(Dog(), Animal) and not isinstance(Dog, Animal))

# user classes deriving from builtins
class MyInt(int): pass
class MyList(list): pass

print(isinstance(MyInt(3), int), isinstance(MyInt(3), MyInt), isinstance(3, MyInt))
print(issubclass(MyInt, int), issubclass(MyInt, (str, int)), issubclass(int, MyInt))
print(isinstance(MyList(), list), isinstance(MyList(), (dict, MyList)))

# union types of builtins (3.10+)
print(isinstance(3, int | str), isinstance(d, int | None), issubclass(bool, str | None))

# errors
try:
    isinstance(5, 3)
except TypeError as e:
    print('TypeError:', e)
try:
    issubclass(d, Animal)
except TypeError as e:
    print('TypeError:', e)
try:
    issubclass(3, int)
except TypeError as e:
    print('TypeError:', e)
try:
    issubclass(int, d)
except TypeError as e:
    print('TypeError:', e)
print(isinstance(d, (Dog, 'x')))   # short-circuits before the bad entry

# None type and type checks
print(isinstance(None, type(None)), isinstance(None, object), type(None) is type(None))

# __class__ attribute
print(d.__class__ is Puppy, d.__class__.__name__, Puppy.__class__ is type)

# reassigning __class__
class A1:
    def who(self):
        return 'A1'

class B1:
    def who(self):
        return 'B1'


obj = A1()
print(obj.who())
obj.__class__ = B1
print(obj.who(), isinstance(obj, B1), isinstance(obj, A1), type(obj).__name__)

# type() vs isinstance with subclasses
print(type(d) is Dog, type(d) == Puppy)

# a class is an instance of type, not of its bases
print(isinstance(Puppy, Dog), isinstance(Puppy, type))

# isinstance on exceptions
class MyErr(ValueError): pass
e = MyErr('x')
print(isinstance(e, ValueError), isinstance(e, Exception), isinstance(e, (KeyError, MyErr)))
print(issubclass(MyErr, Exception), issubclass(MyErr, (LookupError, ArithmeticError)))
