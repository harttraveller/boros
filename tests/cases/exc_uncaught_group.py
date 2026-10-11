# Uncaught ExceptionGroup: CPython prints a boxed traceback whose last line closes the box.


def validate(items):
    errors = []
    for i, item in enumerate(items):
        if not isinstance(item, int):
            errors.append(TypeError('item %d is not an int: %r' % (i, item)))
    if errors:
        raise ExceptionGroup('validation failed', errors)


validate([1, 2, 3])
print('first batch ok')
validate([1, 'two', 3.0])
