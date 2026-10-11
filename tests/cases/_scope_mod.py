"""Helper module docstring."""
print('loading _scope_mod', __name__)
counter = 0
VALUE = 42
_private = 'hidden'


def greet(name):
    return 'hello ' + name


def bump():
    global counter
    counter += 1
    return counter


class Thing:
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return 'Thing(%r)' % (self.v,)


def get_counter_via_globals():
    return globals()['counter']


if __name__ == '__main__':
    print('guard body must not run on import')
