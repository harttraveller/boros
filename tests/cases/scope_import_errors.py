import os
here = os.path.dirname(os.path.abspath(__file__)) + os.sep

# importing a missing module
try:
    import _scope_definitely_missing
except ModuleNotFoundError as e:
    print('ModuleNotFoundError:', e, '| name =', e.name)
try:
    import _scope_pkg.nosuchmod
except ModuleNotFoundError as e:
    print('ModuleNotFoundError:', e, '| name =', e.name)
try:
    from _scope_pkg import nosuchname
except ImportError as e:
    print(type(e).__name__, str(e).split(' (')[0], '| name =', e.name)
print(issubclass(ModuleNotFoundError, ImportError))

# a module whose body raises: the exception propagates, and a later import retries
for i in range(2):
    try:
        import _scope_fails
    except ValueError as e:
        print('ValueError:', e)
try:
    _scope_fails
except NameError as e:
    print('NameError:', e)

# relative imports outside a package
try:
    from . import something
except ImportError as e:
    print('ImportError:', e)
try:
    exec('from .. import x', {'__name__': 'toplevel', '__package__': 'toplevel'})
except ImportError as e:
    print('ImportError:', e)
