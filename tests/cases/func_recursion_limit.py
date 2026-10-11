# A program that raises the recursion limit can recurse a few thousand levels.
import sys

print(sys.getrecursionlimit())
sys.setrecursionlimit(10000)
print(sys.getrecursionlimit())


def depth(n):
    if n == 0:
        return 0
    return 1 + depth(n - 1)


print(depth(3000))


def even(n):
    return True if n == 0 else odd(n - 1)


def odd(n):
    return False if n == 0 else even(n - 1)


print(even(4001))


def build(n):
    return [] if n == 0 else [build(n - 1)]


def nesting(x):
    return 0 if not x else 1 + nesting(x[0])


print(nesting(build(2500)))
