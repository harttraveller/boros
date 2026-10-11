# except (A, B) as e, unbinding of the name after the handler, dynamic handler types.


class A(Exception):
    pass


class B(Exception):
    pass


class C(B):
    pass


def which(exc):
    try:
        raise exc
    except (A, B) as e:
        return 'AB:' + type(e).__name__
    except Exception as e:
        return 'other:' + type(e).__name__


print(which(A()), which(B()), which(C()), which(ValueError()))

# e is unbound after the handler
e = 'before'
try:
    raise A('x')
except A as e:
    pass
try:
    print(e)
except NameError as ne:
    print('NameError:', ne)


def local_unbind():
    err = 1
    try:
        raise B('y')
    except B as err:
        print('inside handler:', err)
    try:
        return err
    except UnboundLocalError as u:
        return 'UnboundLocalError: ' + str(u)


print(local_unbind())


# unbinding happens even if handler raises or returns
def handler_returns():
    try:
        raise A('r')
    except A as exc:
        return exc.args


print(handler_returns())


# saving the exception under another name keeps it alive
def keep():
    try:
        raise C('kept')
    except C as exc:
        saved = exc
    return saved


print(repr(keep().args))

# handler types computed dynamically
handlers = (KeyError, IndexError)
try:
    [][1]
except handlers as h:
    print('dynamic tuple:', type(h).__name__)


def get_type():
    return ZeroDivisionError


try:
    1 / 0
except get_type() as z:
    print('dynamic call:', z)

# nested tuples are not allowed in except clauses
try:
    try:
        raise C('nested')
    except ((ValueError, (KeyError, B)),) as n:
        print('nested tuple:', type(n).__name__)
except TypeError as t:
    print('nested tuple TypeError:', t)

# catching something that isn't an exception class
try:
    try:
        raise A('a')
    except 42:
        pass
except TypeError as t:
    print('TypeError:', t)

try:
    try:
        raise A('a')
    except (A, 'str'):
        print('A matched before the bad entry')
except TypeError as t:
    print('TypeError:', t)


class NotExc:
    pass


try:
    try:
        raise B('b')
    except NotExc:
        pass
except TypeError as t:
    print('TypeError:', t)

# except clause expression is only evaluated when reached
calls = []


def typ(t):
    calls.append(t.__name__)
    return t


try:
    raise C('lazy')
except typ(A):
    pass
except typ(B):
    pass
except typ(C):
    pass
print(calls)

# the name is unbound in comprehension-free nested function scope too
def outer():
    try:
        raise A('closure')
    except A as captured:
        def get():
            return captured
        val = get()
    return val.args


print(outer())

# exception variable in a loop
out = []
for i in range(3):
    try:
        raise B(i)
    except B as ex:
        out.append(ex.args[0])
print(out, 'ex' in dir())

# except with name in class body
class Holder:
    try:
        raise A('cls')
    except A as cls_e:
        msg = str(cls_e)


print(Holder.msg, hasattr(Holder, 'cls_e'))
