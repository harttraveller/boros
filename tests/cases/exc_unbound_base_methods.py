# Exception subclasses calling the base class methods unbound
# (Exception.__init__(self, ...), BaseException.__str__(self), ...).


class OldStyle(Exception):
    def __init__(self, msg, code):
        Exception.__init__(self, msg, code)
        self.code = code


class StrViaBase(ValueError):
    def __str__(self):
        return 'wrapped<' + BaseException.__str__(self) + '>'


class KeyStr(KeyError):
    def __str__(self):
        return 'key ' + KeyError.__str__(self)


e = OldStyle('message', 7)
print(e.args, e.code, str(e))
print(str(StrViaBase('inner')), str(KeyStr('k')))
try:
    raise OldStyle('raised', 1)
except OldStyle as caught:
    print(type(caught).__name__, caught.args, caught.code)
