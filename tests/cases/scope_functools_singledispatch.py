import functools


@functools.singledispatch
def describe(obj):
    return 'object'


@describe.register(int)
def _(obj):
    return 'int'


# 1. dispatch on host types works with an interpreted implementation
print('1', describe(1), describe('s'), describe(True))


class Mine:
    pass


class Child(Mine):
    pass


# 2. registering an interpreted class, dispatching on its (sub)class instances
try:
    @describe.register(Mine)
    def _(obj):
        return 'Mine'
    print('2', describe(Mine()), describe(Child()))
except TypeError as e:
    print('2 TypeError:', str(e).split('.')[0])

# 3. registration through a parameter annotation
try:
    @describe.register
    def _(obj: list):
        return 'list'
    print('3', describe([]))
except TypeError as e:
    print('3 TypeError:', str(e).split(':')[0])


# 4. singledispatchmethod in an interpreted class
class Fmt:
    @functools.singledispatchmethod
    def show(self, arg):
        return 'generic'

    @show.register(int)
    def _(self, arg):
        return 'int %d' % arg


print('4', Fmt().show(5), Fmt().show('x'))
