import sys
import _scope_sysmod

# interpreted modules are registered in sys.modules (during and after loading)
print('_scope_sysmod' in sys.modules)
print(sys.modules.get('_scope_sysmod') is _scope_sysmod)
print(_scope_sysmod.me is _scope_sysmod)
# the running script is sys.modules['__main__']
main = sys.modules[__name__]
print(__name__, main.__name__)
GLOBAL_THING = 'found via sys.modules'
print(getattr(main, 'GLOBAL_THING', 'missing'))
