# Malformed escape sequences and illegal characters in string and bytes
# literals are compile-time SyntaxErrors (raised by compile(), catchable).

import warnings
warnings.simplefilter('ignore')   # invalid-escape SyntaxWarnings
BS = chr(92)
sources = [
    ('truncated \\x', "s = '" + BS + "x4'"),
    ('truncated \\x at end', "s = '" + BS + "x'"),
    ('truncated \\u', "s = '" + BS + "u12'"),
    ('truncated \\U', "s = '" + BS + "U0001F60'"),
    ('\\U out of range', "s = '" + BS + "U00110000'"),
    ('unknown \\N name', "s = '" + BS + "N{NOT A REAL CHARACTER NAME}'"),
    ('\\N without braces', "s = '" + BS + "N'"),
    ('\\N unterminated', "s = '" + BS + "N{BULLET'"),
    ('bytes truncated \\x', "s = b'" + BS + "x4'"),
    ('bytes non-ascii', "s = b'caf" + chr(233) + "'"),
    ('f-string truncated \\x', "s = f'" + BS + "x4{1}'"),
    ('f-string unknown \\N', "s = f'" + BS + "N{NOPE} {1}'"),
    # valid for contrast
    ('valid \\x', "s = '" + BS + "x41'"),
    ('valid \\N', "s = '" + BS + "N{BULLET}'"),
    ('raw \\x', "s = r'" + BS + "x4'"),
    ('raw \\N', "s = r'" + BS + "N{NOPE}'"),
    ('raw bytes \\x', "s = rb'" + BS + "x'"),
    ('bytes \\N', "s = b'" + BS + "N{NOPE}'"),
    # octal escapes above 0o377: a warning; bytes keep the low 8 bits
    ('str octal 777', "s = '" + BS + "777'"),
    ('bytes octal 777/400', "s = b'" + BS + "777" + BS + "400'"),
]
for label, src in sources:
    try:
        ns = {}
        exec(compile(src, '<esc>', 'exec'), ns)
        print(label, '->', ascii(ns['s']))
    except SyntaxError:
        print(label, '-> SyntaxError')
    except Exception as e:
        print(label, '-> wrong exception', type(e).__name__)
