import builtins

# 1. names added to the builtins module become visible everywhere
builtins.scope_added_builtin = 42
try:
    print('1', scope_added_builtin)
except NameError as e:
    print('1 NameError:', e)


def f():
    return scope_added_builtin + 1


try:
    print('1b', f())
except NameError as e:
    print('1b NameError:', e)
del builtins.scope_added_builtin
try:
    scope_added_builtin
except NameError as e:
    print('1c NameError:', e)

# 2. shadowing and un-shadowing a builtin at module level
len = lambda x: 'shadowed'
print('2', len([1, 2]))
del len
print('2b', len([1, 2]))


def local_shadow():
    list = 'local list'
    return list


print('2c', local_shadow(), list('ab'))

# 3. in the main module __builtins__ is the builtins module itself
print('3', __builtins__ is builtins, __builtins__.abs(-2) if hasattr(__builtins__, 'abs') else 'no attr')
