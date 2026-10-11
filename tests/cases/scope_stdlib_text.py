import json
import re
import string

# string module
print(string.ascii_letters[:3], string.digits, string.punctuation[:5], string.capwords('a  b-c d'))
t = string.Template('$who likes ${what}!')
print(t.substitute(who='tim', what='kung pao'), t.safe_substitute(who='x'))


class Ctx:
    def __getitem__(self, k):
        return k.upper()

    def __contains__(self, k):
        return True

    def keys(self):
        return []


print(string.Template('$a-$b').substitute({'a': 1, 'b': 2}))
fmt = string.Formatter()
print(fmt.format('{0}-{name}', 'p', name='n'), list(fmt.parse('a{b}c'))[0][:2])

# re with interpreted callbacks
counter = [0]


def repl(m):
    counter[0] += 1
    return m.group(0).upper() + str(counter[0])


print(re.sub(r'[aeiou]', repl, 'banana split'))
print(re.sub(r'(\w+)@(\w+)', lambda m: m.group(2) + ' at ' + m.group(1), 'joe@host and ann@srv'))
print(re.subn(r'\d', lambda m: str(int(m.group()) * 2), 'a1b2c3'))
pat = re.compile(r'(?P<key>\w+)=(?P<val>\d+)')
print([m.groupdict() for m in pat.finditer('a=1, bb=22')], pat.findall('x=5 y=6'))
m = pat.search('zz q=42')
print(m.group('key'), m.span(), m.start('val'), m.groups(), m.lastgroup)
print(re.split(r'[,;]\s*', 'a, b;c'), re.fullmatch(r'\d+', '123') is not None, re.match('x', 'yx'))
print(re.sub(r'(?i)HELLO', 'bye', 'hello Hello'), re.escape('a.b*c'), re.findall(r'(a)(b)?', 'ab a'))
print(pat.sub(lambda mm: '%s:%s' % (mm['val'], mm['key']), 'k=1;j=2'), re.IGNORECASE | re.MULTILINE)
try:
    re.compile('(')
except re.error as e:
    print('re.error:', e)


# json with interpreted hooks
class Pt:
    def __init__(self, x, y):
        self.x = x
        self.y = y


def enc(o):
    if isinstance(o, Pt):
        return {'__pt__': [o.x, o.y]}
    if isinstance(o, set):
        return sorted(o)
    raise TypeError('cannot encode %s' % type(o).__name__)


s = json.dumps({'p': Pt(1, 2), 's': {3, 1}, 'n': None, 'b': True, 'f': 1.5}, default=enc, sort_keys=True)
print(s)


def hook(d):
    if '__pt__' in d:
        return Pt(*d['__pt__'])
    return d


back = json.loads(s, object_hook=hook)
print(type(back['p']).__name__, back['p'].x, back['s'], back['n'])
print(json.dumps([1, 'two', {'k': [None]}], indent=2))
print(json.dumps({'b': 1, 'a': 2}, separators=(',', ':'), sort_keys=True), json.loads('[1.5, "x", null, true]'))
print(json.loads('{"a": 1}', object_pairs_hook=lambda pairs: [k for k, v in pairs]))
print(json.loads('1.25', parse_float=lambda s: 'F' + s), json.dumps('é'), json.dumps('é', ensure_ascii=False))
try:
    json.dumps(object(), default=enc)
except TypeError as e:
    print('TypeError:', e)
try:
    json.loads('{bad json}')
except json.JSONDecodeError as e:
    print('JSONDecodeError:', e)
