# Triple-quoted strings and adjacent literal concatenation.

a = '''single 'quotes' inside, and "double" too'''
b = """double "quotes" inside, and 'single' too"""
c = '''it's ''two'' quotes'''
d = """ends with an escaped quote\""""
e = '''''starts with two quotes'''
f = '''multi
line
  indented
'''
g = """with \
continuation"""
h = '''escape \t tab \n newline \x41 \u00e9'''
i = """'"'"'"'"""
j = ''''''
k = """"""
for name, v in [('a', a), ('b', b), ('c', c), ('d', d), ('e', e), ('f', f), ('g', g),
                ('h', h), ('i', i), ('j', j), ('k', k)]:
    print(name, repr(v), len(v))


# adjacent literal concatenation
s1 = 'abc' 'def'
s2 = 'abc' "def" '''ghi''' """jkl"""
s3 = ('first '
      'second '   # comment between pieces
      "third")
s4 = 'back' \
     'slash'
s5 = r'\raw' '\tnormal' r'\raw2'
s6 = ''  ''  'x'  ''
print(s1, s2, s3, s4, repr(s5), repr(s6), sep='|')
x = 7
s7 = 'value: ' f'{x}' ' units' f' ({x * 2})'
s8 = f'{x}' 'literal {not a field}' f'{{braces}}'
s9 = ('multi-line '
      f'f-string {x} '
      'concat '
      rf'raw \{x}')
print(s7, s8, s9, sep='|')
print(len('a' 'b' 'c'), ('a' 'b').upper(), 'x' 'y' in 'wxyz')
# concatenation binds tighter than any operator
print('a' 'b' * 2, 'a' 'b' + 'c' 'd')
words = ['one' 'two', 'three'
         'four']
print(words)
print({'k' 'ey': 'v' 'al'})
# implicit concatenation in function call arguments
print('sep' 'arated', 'args', sep='' '-' '')
