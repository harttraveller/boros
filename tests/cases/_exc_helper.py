# Helper module for exc_ cases: exception classes and functions that raise.


class HelperError(Exception):
    """An error defined in a helper module."""


class DetailedError(HelperError):
    def __init__(self, code, detail):
        super().__init__(code, detail)
        self.code = code
        self.detail = detail

    def __str__(self):
        return '[%d] %s' % (self.code, self.detail)


class Outer:
    class Nested(LookupError):
        pass


def fail(msg):
    raise HelperError(msg)


def fail_detailed():
    raise DetailedError(42, 'detailed failure')


def fail_nested():
    raise Outer.Nested('nested class')


def fail_host():
    return {}['helper-key']


def call_back(f):
    try:
        return f()
    finally:
        pass
