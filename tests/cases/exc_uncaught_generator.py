# Uncaught exception raised inside an interpreted generator consumed by a host builtin.


class GenFailure(ValueError):
    pass


def numbers():
    yield 1
    yield 2
    raise GenFailure('generator broke after 2')


print(sum(x for x in range(3)))
print(sorted(numbers()))
