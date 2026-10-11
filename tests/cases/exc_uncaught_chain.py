# Uncaught exception with a cause chain; the final line is the last exception raised.


class StorageError(Exception):
    pass


def load():
    try:
        open('/nonexistent/boros/file')
    except OSError as e:
        raise StorageError('could not load config') from e


print('loading')
load()
