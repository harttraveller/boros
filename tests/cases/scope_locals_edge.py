# 1. in a class body, locals() *is* the class namespace: writes create attributes
class Generated:
    for _n in ('red', 'green'):
        locals()[_n.upper()] = _n
    del _n


print('1', getattr(Generated, 'RED', 'missing'), getattr(Generated, 'GREEN', 'missing'))


class ViaVars:
    vars()['made'] = 'by vars()'


print('1b', getattr(ViaVars, 'made', 'missing'))


# 2. locals() in a function includes free variables it uses
def outer():
    free = 'outer value'
    own = 1

    def inner():
        mine = free + '!'
        return sorted(locals().items())
    return inner()


print('2', outer())


# 3. dir() without arguments in a function lists the same names
def outer2():
    free = 1

    def inner():
        free
        local = 2
        return dir()
    return inner()


print('3', outer2())
