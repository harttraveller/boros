"""Helper module for the func_ cases."""


def helper(x):
    "helper doc"
    return x + 1


class Thing:
    "Thing doc"

    def method(self):
        "method doc"
        return 'method'

    def __call__(self, v):
        return v * 10


def make_closure(n):
    def inner(x):
        return x + n
    return inner
