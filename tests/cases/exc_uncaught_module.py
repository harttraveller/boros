# Uncaught custom exception raised inside an imported helper module.
import _exc_helper

try:
    _exc_helper.fail('caught first')
except _exc_helper.HelperError as e:
    print('caught', type(e).__name__, e, type(e).__module__)

print('now uncaught')
_exc_helper.fail('helper module failure')
