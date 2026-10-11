# sys.exit with a non-int, non-str object: str() of it goes to stderr, status 1.
import sys


class Reason:
    def __str__(self):
        return 'custom reason object'


print('exit with object')
sys.exit(Reason())
