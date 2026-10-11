# Concrete subclasses of abc.ABC (and typing.Generic / Protocol) behave like
# ordinary classes, including constructors that take arguments.
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Protocol

T = TypeVar('T')


class Shape(ABC):
    @abstractmethod
    def area(self):
        ...

    def describe(self):
        return '%s with area %s' % (type(self).__name__, self.area())


class Square(Shape):
    def __init__(self, side):
        self.side = side

    def area(self):
        return self.side ** 2


class Rect(Shape):
    def __init__(self, w, h=1, *, label='r'):
        super().__init__()
        self.w, self.h, self.label = w, h, label

    def area(self):
        return self.w * self.h


print(Square(3).describe(), Rect(2, 5, label='x').describe(), Rect(w=4).area())
print(isinstance(Square(1), Shape), issubclass(Rect, ABC), [c.__name__ for c in Square.__mro__])


class Box(Generic[T]):
    def __init__(self, item):
        self.item = item

    def get(self):
        return self.item


print(Box(5).get(), Box(item='kw').get(), isinstance(Box(1), Box))


class Greets(Protocol):
    def greet(self) -> str:
        ...


class English(Greets):
    def __init__(self, name):
        self.name = name

    def greet(self):
        return 'hello ' + self.name


print(English('bob').greet())
