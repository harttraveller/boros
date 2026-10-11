# abc: abstract methods prevent instantiation; __abstractmethods__;
# register() of virtual subclasses; ABCMeta as metaclass.
import abc
from abc import ABC, abstractmethod


class Shape(ABC):
    @abstractmethod
    def area(self):
        ...

    @property
    @abstractmethod
    def name(self):
        ...


class Partial(Shape):
    def area(self):
        return 0


class Full(Partial):
    @property
    def name(self):
        return 'full'


print(sorted(Shape.__abstractmethods__), sorted(Partial.__abstractmethods__), sorted(Full.__abstractmethods__))
print(Full().name, Full().area(), Shape.area.__isabstractmethod__)
for cls in (Shape, Partial):
    try:
        cls()
        print('instantiated', cls.__name__)
    except TypeError as e:
        print('TypeError:', e)


class Base(metaclass=abc.ABCMeta):
    @abstractmethod
    def run(self):
        pass


try:
    Base()
    print('instantiated Base')
except TypeError as e:
    print('TypeError:', e)
print(type(Shape).__name__, type(Base).__name__)


class Iface(ABC):
    pass


Iface.register(int)
print(isinstance(3, Iface), issubclass(int, Iface), issubclass(str, Iface))
