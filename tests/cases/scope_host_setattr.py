import argparse
import functools


# 1. a class-based decorator using functools.update_wrapper(self, func):
#    host code sets __module__, __name__, __doc__, __wrapped__ ... on an interpreted instance
class CountCalls:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.calls = 0

    def __call__(self, *args):
        self.calls += 1
        return self.__wrapped__(*args)


try:
    @CountCalls
    def hello(name):
        """Say hello."""
        return 'hello ' + name

    print('1', hello('a'), hello('b'), hello.calls, hello.__name__, hello.__doc__)
except AttributeError as e:
    print('1 AttributeError:', e)


# 2. argparse storing parsed values on an interpreted namespace object
class Opts:
    verbose = False


p = argparse.ArgumentParser(prog='demo')
p.add_argument('--count', type=int, default=1)
p.add_argument('-v', '--verbose', action='store_true')
try:
    o = p.parse_args(['--count', '3', '-v'], namespace=Opts())
    print('2', o.count, o.verbose, type(o).__name__)
except AttributeError as e:
    print('2 AttributeError:', e)
ns = p.parse_args(['--count', '7'])
print('3', ns.count, ns.verbose)
