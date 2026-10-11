# f-string replacement-field edge cases (Python 3.12+ grammar):
#  * strings with escaped backslashes / quotes inside the expression part
#  * whitespace between a conversion and ':' or '}'
#  * '#' comments inside multi-line expression parts

x = 5
print(f'{"\\"}')
print(f"{'\\' * 3}")
print(f'{"a\\" + "b"}')
print(f'{"\\\\"}|{len("\\\\")}')
print(f'{"q\"q"} {"\'"}')
print(f'{x:{"\\"}>4}|')
print(f'{x!r }|')
print(f'{x!s :>4}|')
print(f'{x!r:>3}|')
print(f'{x # comment
}')
print(f'''{
    x  # a comment: with a colon, a } brace and 'quote'
    + 1
}''')
print(f"""{
    [i  # loop variable
     for i in range(3)]
}""")
