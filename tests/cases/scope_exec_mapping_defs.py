# exec() with a locals mapping that is not a dict (only __getitem__ and
# __setitem__): names, functions, classes and comprehensions all work.


class Mapping:
    def __init__(self):
        self.d = {'base': 10}

    def __getitem__(self, k):
        return self.d[k]

    def __setitem__(self, k, v):
        self.d[k] = v


m = Mapping()
src = '''
def f():
    return 1
class C:
    a = 2
    def m(self):
        return self.a
double = lambda v: v * 2
r = f() + C().m() + double(base)
squares = [base + i * i for i in range(3)]
'''
exec(src, {}, m)
print(sorted(m.d), m.d['r'], m.d['squares'], m.d['C'].__qualname__, m.d['f'].__qualname__)
try:
    exec('def g():\n    return base\nx = g()', {}, m)
except NameError as e:
    print('NameError:', e)
