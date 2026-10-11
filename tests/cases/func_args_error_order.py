# CPython processes keyword arguments before it checks the number of
# positional arguments, and reports positional-only names passed as keywords
# in preference to an unexpected keyword.


def check(label, thunk):
    try:
        thunk()
    except TypeError as e:
        print(label, '-> TypeError:', e)


def f2(a, b=2):
    return (a, b)


def f9(a, b=1, *, c, d=2):
    return 1


def po2(a, b, /):
    return 1


# keyword errors win over "too many positional arguments"
check('unexpected beats too many', lambda: f2(1, 2, 3, x=1))
check('multiple values beats too many', lambda: f2(1, 2, a=3))
check('multiple values beats too many 2', lambda: f2(1, 2, 3, a=3))
check('kwonly unexpected beats too many', lambda: f9(1, 2, 3, x=1))


# a positional-only name passed by keyword is reported even when another
# keyword is unexpected, whatever the keyword order
check('posonly before unexpected', lambda: po2(a=1, x=2))
check('unexpected before posonly', lambda: po2(x=2, a=1))
check('both posonly + unexpected', lambda: po2(b=1, a=2, zz=3))
# the positional-only names are listed in parameter order
check('posonly names in parameter order', lambda: po2(b=2, a=1))


# the first problematic keyword (in call order) decides the error
def f3(a, b, c):
    return 1


check('dup before unexpected', lambda: f3(1, a=2, zz=3, b=1, c=1))
check('unexpected before dup', lambda: f3(1, zz=3, a=2, b=1, c=1))
