# Bytes literals: escapes, raw bytes, concatenation, and errors.

def show(label, b):
    print(label, repr(b), len(b), list(b)[:10], type(b).__name__)

show('plain', b'hello')
show('B', B"world")
show('esc', b'\n\t\r\\\'\"\a\b\f\v\0')
show('hex', b'\x00\x7f\x80\xff\xAb')
show('octal', b'\101\102\103\1\12\177\377')
show('u_is_literal', b'\\u0041'.replace(b'\\\\', b'\\'))
show('unknown', b'\\q\\d'.replace(b'\\', b'/'))
show('cont', b'ab\
cd')
show('triple', b'''tri
ple''')
show('triple_dq', B"""a"b'c""")
show('raw', rb'\x00\n')
show('raw2', BR'\\')
show('concat', b'ab' b'cd' rb'\e')
show('concat_lines', (b'one'
                      b'two'
                      br'\three'))
show('empty', b'')
print(b'abc'[0], b'abc'[1:], b'a' in b'cat', b'\x41' == b'A')
print(b'%d-%s' % (5, b'x'))
print(bytes([0, 1, 255]) == b'\x00\x01\xff')
print(b'\xe2\x82\xac'.decode('utf-8') == '\N{EURO SIGN}')
print(bytearray(b'xyz'), b'caf\xc3\xa9'.decode())

# \u, \U and \N are not escapes in bytes: they stay as backslash + letter
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for src in ["b'\\u0041'", "b'\\U00000041'", "b'\\N{BULLET}'", "b'\\q'"]:
        v = eval(src)
        print(src, repr(v), len(v))
