# Uncaught exception whose class (in a helper module) overrides __str__.
from _exc_helper import fail_detailed, DetailedError

try:
    fail_detailed()
except DetailedError as e:
    print(str(e), e.code, e.args)
fail_detailed()
