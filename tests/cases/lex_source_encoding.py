# Source encodings: a UTF-8 byte order mark and PEP 263 coding
# declarations, in imported module files and in bytes passed to exec().

try:
    import _lex_bom_mod
    print('bom module:', _lex_bom_mod.VALUE)
except SyntaxError:
    print('bom module: SyntaxError')

try:
    import _lex_latin1_mod
    print('latin-1 module:', _lex_latin1_mod.VALUE, _lex_latin1_mod.NAME)
except (SyntaxError, UnicodeDecodeError) as e:
    print('latin-1 module:', type(e).__name__)

sources = [
    ('utf-8 bytes', b'v = "caf\xc3\xa9"'),
    ('bom bytes', b'\xef\xbb\xbfv = "bom"'),
    ('latin-1 cookie', b'# -*- coding: latin-1 -*-\nv = "caf\xe9"'),
    ('cookie on line 2', b'#!/usr/bin/env python\n# vim: set fileencoding=iso-8859-15 :\nv = "\xa4uro"'),
    ('utf-8 cookie', b'# coding=utf-8\nv = "caf\xc3\xa9"'),
    ('bom str', '﻿v = "bom in str"'),
]
for label, src in sources:
    ns = {}
    try:
        exec(src, ns)
        print(label, '->', ns['v'])
    except SyntaxError:
        print(label, '-> SyntaxError')
    except UnicodeDecodeError:
        print(label, '-> UnicodeDecodeError')
