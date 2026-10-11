# Implicit line joining inside brackets, backslash continuation, comments,
# semicolons, blank lines, and statements on one line.
# -*- coding: utf-8 -*-   (a coding-style comment, ignored here)

total = (1 +
         2 +   # a comment inside parentheses
         3)
print(total)

items = [
    1,
    2,

    # a comment line inside a list

    3,
]
print(items)

d = {
    'a': 1,   # trailing comment
    'b':
        2,
}
print(d)

def f(a,
      b=2,
          c=3):   # odd indentation inside brackets is fine
    return a + b + c
print(f(1,
        c=10))

x = 1 + \
    2 + \
    3
print(x)

if x > 1 and \
   x < 10:
    print('backslash in condition')

y = \
    5
print(y)

s = 'text' \
    ' more'
print(s)

with open(__file__) as fh, \
     open(__file__) as fh2:
    print(len(fh.read()) == len(fh2.read()))

a = 1; b = 2; c = a + b
print(a, b, c)
print('one'); print('two');
if a: print('if-a'); print('still if-a')
for i in range(2): print('loop', i); print('loop2', i)
while False: pass
def g(): return 'g'
class K: v = 1; w = 2
print(g(), K.v, K.w)
try: z = 1 / 0
except ZeroDivisionError: print('zde')
finally: print('finally')

# comment with quotes ' " ''' and a backslash \
print('after comment with backslash')
#comment-without-space
    # indented comment at module level (allowed)
print('#not a comment', "# nor this")   # but this is

def h():
    # comment before first statement
    x = 1
        # over-indented comment
    return x
# comment between function and call
print(h())

nested = [[1, 2,
           3], (4,
                5), {6:
                     7}]
print(nested)
call = max(
    1,
    2,
)
print(call)
t = (
)
print(t)
lam = (lambda
       q: q * 2)
print(lam(4))
print(1 if True
      else 2)
result = [i
          for i in range(3)
          if i]
print(result)
print(  'spaces'  ,  'everywhere'  )
print	('tab before paren')
v	=	3	;	print(v)
long_expr = 1 \
+ 2
print(long_expr)
