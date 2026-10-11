# Uncaught KeyError raised by host code called from a helper module.
import _exc_helper

print('host error next')
_exc_helper.call_back(_exc_helper.fail_host)
