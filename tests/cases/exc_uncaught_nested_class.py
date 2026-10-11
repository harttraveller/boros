# Uncaught exception whose class is nested in another class (qualname in the message).
import _exc_helper

print(_exc_helper.Outer.Nested.__qualname__, _exc_helper.Outer.Nested.__module__)
_exc_helper.call_back(_exc_helper.fail_nested)
