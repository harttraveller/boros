# sys.exit with a string message: printed to stderr, exit status 1.
import sys


def shutdown(reason):
    try:
        sys.exit('fatal: ' + reason)
    finally:
        print('finally runs before exit')


print('start')
shutdown('disk full')
print('not reached')
