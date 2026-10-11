# sys.exit with an int code propagates through handlers that don't catch it.
import sys


def work():
    try:
        sys.exit(7)
    except Exception:
        print('Exception does not catch SystemExit')


try:
    work()
except SystemExit as e:
    print('caught SystemExit', e.code, e.args, repr(e))

try:
    raise SystemExit
except SystemExit as e:
    print('bare SystemExit code:', e.code)

try:
    sys.exit(None)
except SystemExit as e:
    print('None code:', e.code)

try:
    sys.exit(1, 2)
except TypeError as e:
    print('TypeError:', e)
except SystemExit as e:
    print('SystemExit args', e.args)

try:
    sys.exit((1, 2))
except SystemExit as e:
    print('tuple code:', e.code)


class Quit(SystemExit):
    pass


try:
    raise Quit(9)
except SystemExit as e:
    print(type(e).__name__, e.code)

print('exiting with 5')
sys.exit(5)
