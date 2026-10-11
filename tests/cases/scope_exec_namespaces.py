import collections

# 1. a custom '__builtins__' in the globals dict restricts what is visible
try:
    exec("print('restricted print ok')\nlen('ab')", {'__builtins__': {'print': print}})
    print('1 len was visible')
except NameError as e:
    print('1 NameError:', e)

# 2. a defaultdict as locals: missing names come from __missing__
dd = collections.defaultdict(lambda: 'dflt')
try:
    print('2', eval('missing_name', {}, dd))
except NameError as e:
    print('2 NameError:', e)


# 3. any mapping (only __getitem__ is needed) can serve as locals
class Upper:
    def __getitem__(self, key):
        if key.startswith('v_'):
            return key[2:].upper()
        raise KeyError(key)


try:
    print('3', eval('v_abc + v_d', {}, Upper()))
except Exception as e:
    print('3', type(e).__name__, e)

# 4. 'single' mode prints the repr of expression statements
print('4')
exec(compile('1 + 2', '<single>', 'single'))
exec(compile('"text"', '<single>', 'single'))
exec(compile('None', '<single>', 'single'))

# 5. a comprehension in eval code whose locals mapping is not a dict


class Upper2:
    def __getitem__(self, key):
        if key == 'n':
            return 3
        raise KeyError(key)


try:
    print('5', eval('[i for i in range(n)]', {}, Upper2()), eval('(i for i in range(n))', {}, Upper2()).__class__.__name__)
except Exception as e:
    print('5', type(e).__name__, e)
