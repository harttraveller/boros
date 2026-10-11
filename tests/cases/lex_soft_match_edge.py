# `match` soft keyword: the statement is recognised by the colon that ends
# the logical line, even when the subject itself contains colons
# (lambda, slices inside brackets, dict displays).

match lambda: 0:
    case _:
        print('lambda subject')
data = [1, 2, 3]
match data[1:]:
    case [2, 3]:
        print('slice subject')
match {1: 'a'}:
    case {1: v}:
        print('dict subject', v)
match (lambda x: x)(5):
    case 5:
        print('called lambda subject')
match = {'k': lambda: 'v'}
print(match['k']())
