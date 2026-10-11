# Argument validation of type(name, bases, dict).
for args in [('A', 'not a tuple', {}), ('A', (), []), (5, (), {})]:
    try:
        type(*args)
        print('no error')
    except TypeError as e:
        print('TypeError:', e)
