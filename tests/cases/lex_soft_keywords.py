# Soft keywords (match, case, type, _) used as ordinary names, and match
# statements whose subject looks like a call/subscript/tuple.
import re

match = re.match(r'(\w+)-(\d+)', 'item-42')
print(match.group(1), match[2])
match = 'reassigned'
print(match)
match += '!'
print(match)
match: str = 'annotated'
print(match)
case = 3
case *= 2
print(case)
type = 'shadowed type'
print(type)
del type
print(type(5).__name__)
_ = 'underscore'
print(_)
_, second = (1, 2)
print(_, second)
for _ in range(2):
    pass
print(_)


def match(a, b=0):
    return a + b


print(match(1), match(1, b=2))
print(match (3))
match(4)
match.attr = 'function attribute'
print(match.attr)
print([match for match in range(3)])
lst = [10, 20]


def case(*args):
    return args


print(case(1, 2), case())

match = lst
match[0] = 99
print(match, match[0], match[-1:])
match, case = 'm', 'c'
print(match, case)
print(match if case else None)
print({match: case})
d = {'match': 1, 'case': 2, 'type': 3, '_': 4}
print(d['match'], dict(match=1, case=2, type=3, _=4))


class Obj:
    match = 'class attr'
    case = 'case attr'
    type = 'type attr'

    def _(self):
        return 'method _'


o = Obj()
print(o.match, o.case, o.type, o._())

# match statements with subjects that could be mistaken for expressions
x = (1, 2)
match x:
    case (1, 2):
        print('tuple matched')
match (x):
    case (a, b):
        print('parenthesized subject', a, b)
match x[0], x[1]:
    case 1, 2:
        print('tuple subject')
match [1, 2]:
    case [1, *rest]:
        print('list subject', rest)
match -1:
    case -1:
        print('negative subject')
match {'k': 'v'}:
    case {'k': v}:
        print('dict subject', v)
match lst:
    case [first, *_]:
        print('first of lst', first)
match = {'match': 'case'}
match match:
    case {'match': case}:
        print('match on name match', case)
match not None:
    case True:
        print('not-expression subject')
match 'type':
    case type:
        print('captured into type:', type)
del type
match 5:
    case _ if _ := 'walrus-guard':
        print('guard', _)

type X = int
print('type alias statement parsed')


def type_param_func[T](a: T) -> T:
    return a


print(type_param_func('generic'))
