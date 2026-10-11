# Python 3.13 suggests a close parameter name for an unexpected keyword.


def check(label, thunk):
    try:
        thunk()
    except TypeError as e:
        print(label, '-> TypeError:', e)


def f1(a):
    return a


def longname(alpha, beta):
    return 1


def kwo(*, verbose=False, value=0):
    return verbose


def po(first, /, second):
    return 1


class Widget:
    def resize(self, width, height):
        return width * height


check('one letter', lambda: f1(aa=1))
check('typo', lambda: longname(alpha=1, betaa=2))
check('kwonly typo', lambda: kwo(verbos=True))
check('case', lambda: kwo(Value=1))
check('method typo', lambda: Widget().resize(1, heigth=2))
check('too far, no suggestion', lambda: longname(alpha=1, zzzzzz=2))
# positional-only names are not suggested
check('posonly not suggested', lambda: po(1, firs=2))
