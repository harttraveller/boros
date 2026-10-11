# Error messages and protocol fallbacks of builtins applied to interpreted objects.


class Num:
    def __init__(self, v):
        self.v = v

    def __index__(self):
        return self.v

    def __rpow__(self, b):
        return 'rpow'


class Plain:
    pass


# 1. three-argument pow() does not use __rpow__; the message names the classes
try:
    print('1', pow(2, Num(3), 5))
except TypeError as e:
    print('1 TypeError:', e)
# 2. complex() of an unsupported object
try:
    complex(Plain())
except TypeError as e:
    print('2 TypeError:', e)
# 3. 'in' on an object without __contains__/__iter__/__getitem__
try:
    'x' in Plain()
except TypeError as e:
    print('3 TypeError:', e)
# 4. sequence repetition by an object with __index__
try:
    print('4', 'ab' * Num(2), [0] * Num(3), Num(2) * (1,), b'x' * Num(2))
except TypeError as e:
    print('4 TypeError:', e)
# 5. sequence repetition by an object without __index__
for seq in ('a', [1], (1,)):
    try:
        seq * Plain()
    except TypeError as e:
        print('5 TypeError:', e)
