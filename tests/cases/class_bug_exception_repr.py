# repr() of instances of user exception classes uses the user class name.

class AppError(Exception):
    pass


class NotFound(AppError, KeyError):
    def __init__(self, key):
        super().__init__('not found: %r' % (key,))
        self.key = key


class Custom(ValueError):
    pass


print(repr(AppError()), repr(AppError('a')), repr(AppError('a', 2)))
print(repr(NotFound('k')), repr(Custom(1)))
print([AppError('in list')], {'e': Custom('in dict')})
print('%r' % (AppError('pct'),), f'{AppError("fs")!r}')
try:
    raise Custom('raised')
except Exception as e:
    print(repr(e), str(e), e.args)
