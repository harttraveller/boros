# Indentation: tabs, mixed indentation widths, deep nesting, dedenting
# several levels at once, form feeds, and blank/comment lines.

def tabs():
	x = 1
	if x:
		x += 1
		if x > 1:
			x += 10
	return x
print(tabs())

def two_spaces():
  y = 0
  for i in range(3):
    if i % 2:
      y += i
    else:
        y -= 1     # deeper indent in the else branch
  return y
print(two_spaces())

def deep():
    if True:
        if True:
            if True:
                if True:
                    v = 'deep'
    return v         # dedent four levels at once
print(deep())

class A:
    def m(self):
        return 'm'


    # blank lines and comments between methods

    def n(self):

        return 'n'
print(A().m(), A().n())

if True:
    pass
# comment at column 0 inside nothing
else_value = 1
print(else_value)

def trailing_ws():
    a = 1

    return a
print(trailing_ws())

def run(src):
    ns = {}
    try:
        exec(src, ns)
        return ns.get('r')
    except SyntaxError as e:
        return 'SyntaxError'

# (tab/space consistency and form feeds are tested in lex_indent_errors.py)
# tabs on every line of a block
print(run('if 1:\n\tr = 1\n\tr += 1\n'))
print(run('r = 0\nif 1:\n    r = 5\n\f\nr += 1\n'))
# indentation consisting of a single space, then many
print(run('if 1:\n r = 7\nif r:\n                                r = 8\n'))
# carriage-return / CRLF line endings
print(run('if 1:\r\n    r = 9\r\n    r += 1\r\n'))
print(run('if 1:\r    r = 11\r'))
# no trailing newline at end of an indented block
print(run('if 1:\n    r = 12'))
print(run('def q():\n    return 13\nr = q()'))
# trailing comment without newline after an indented block
print(run('if 1:\n    r = 14\n# done'))
# continuation lines do not affect indentation
print(run('if 1:\n    r = 1 + \\\n2\n    r += 13\n'))
# a line with only whitespace inside a block
print(run('if 1:\n    r = 16\n        \n    r += 1\n'))
# dedent back to an intermediate level
print(run('if 1:\n    if 1:\n        r = 18\n    r += 1\n'))
