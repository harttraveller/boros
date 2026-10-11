# String escape sequences in ordinary (non-raw) string literals.

def show(label, s):
    print(label, repr(s), len(s), [ord(c) for c in s][:12])

show('simple', '\n\t\r\\\'\"\a\b\f\v')
show('dq', "\"quoted\" and 'single'")
show('sq', '\'quoted\' and "double"')
show('hex', '\x41\x62\x7e\x00\xff\xFF\xaB')
show('octal1', '\0\7\77\101\1234')
show('octal_max', '\377\376')
show('octal_short', '\08\19')
show('u16', '\u0041\u00e9\u20ac\uFFFD')
show('u32', '\U00000041\U0001F600\U0010ffff')
show('named', '\N{LATIN SMALL LETTER E WITH ACUTE}\N{EURO SIGN}\N{BULLET}')
show('named_lower', '\N{em dash}\N{snowman}')
show('named_alias', '\N{LINE FEED}\N{NBSP}')
show('named_emoji', '\N{GRINNING FACE}')
show('mixed', 'a\tb\x43\u0044\N{DIGIT ONE}\62\n')
show('continuation', 'abc\
def\
ghi')
show('cont_dq', "one \
two")
show('backslash_end', 'ends with backslash\\')
show('double_bs', '\\n is not a newline')
show('bs_x_upper', '\\X41')
show('hash_inside', '# not a comment')
show('unicode_src', 'café 日本語 😀')
print(len('\U0001F600'), len('\u00e9'), len('e\u0301'))
show('empty', '')
show('empty_dq', "")
show('u_prefix', u'unicode \u00e9')
show('U_prefix', U'X\x59')
# escapes that are not recognised are kept verbatim
show('unknown', '\\q \\w'.replace('\\', '/'))
print('\101BC' == 'ABC', '\x41' == 'A', '\u0041' == 'A', '\N{LATIN CAPITAL LETTER A}' == 'A')
print('tab\there', 'nl\nhere', sep='|')
print('carriage\rreturn'.split('\r'))
print(repr('\x7f\x80\x9f\xa0\xad'))
print(ascii('\u2028\u2029\x85'))
s = 'line1\nline2\n\tindented'
print(s.splitlines())
# escape sequences decoded at compile time inside exec()'d source
src = "s = '\\x41\\u00e9\\N{BULLET}\\101\\n'\nprint(repr(s), len(s))\n"
exec(src)
# invalid escape sequences that warn (not error) still produce the backslash
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    ns = {}
    exec("t = '\\d\\s\\%'", ns)
    print(repr(ns['t']), len(ns['t']))
