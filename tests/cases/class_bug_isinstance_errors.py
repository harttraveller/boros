# isinstance/issubclass must reject a non-class second argument even when
# the first argument is an instance/subclass of an interpreted class.

class Animal:
    pass


class Dog(Animal):
    pass


d = Dog()
cases = [
    ('isinstance(d, 3)', lambda: isinstance(d, 3)),
    ("isinstance(d, 'Dog')", lambda: isinstance(d, 'Dog')),
    ("isinstance(d, (int, 'x'))", lambda: isinstance(d, (int, 'x'))),
    ('isinstance(d, d)', lambda: isinstance(d, d)),
    ('issubclass(Dog, d)', lambda: issubclass(Dog, d)),
    ('issubclass(Dog, 3)', lambda: issubclass(Dog, 3)),
    ("issubclass(Dog, (int, 'x'))", lambda: issubclass(Dog, (int, 'x'))),
    ('issubclass(d, Animal)', lambda: issubclass(d, Animal)),
    ('isinstance(d, (Dog, 3))', lambda: isinstance(d, (Dog, 3))),
]
for text, f in cases:
    try:
        print(text, '->', f())
    except TypeError as e:
        print(text, '-> TypeError:', e)
