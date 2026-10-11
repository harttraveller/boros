# 1. __all__ may name a submodule that has not been imported yet: it is imported
try:
    from _scope_starpkg import *
    print(top, mod_a.A)
except Exception as e:
    print('1 unexpected', type(e).__name__, e)
# 2. import * is only allowed at module level
for src in ['def f():\n    from math import *\n', 'class C:\n    from math import *\n']:
    try:
        compile(src, '<src>', 'exec')
        print('2 compiled')
    except SyntaxError as e:
        print('2 SyntaxError:', e.msg)
# 3. __all__ naming a missing attribute raises AttributeError
try:
    from _scope_star_bad import *
except Exception as e:
    print('3', type(e).__name__, e)
