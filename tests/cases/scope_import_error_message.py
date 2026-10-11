import os
here = os.path.dirname(os.path.abspath(__file__)) + os.sep
# CPython includes the module file in the message
try:
    from _scope_err_target import absent
except ImportError as e:
    print('ImportError:', str(e).replace(here, ''))
