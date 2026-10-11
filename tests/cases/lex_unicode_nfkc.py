# Identifiers are NFKC-normalized by the tokenizer (PEP 3131): different
# spellings of the same normalized name are the same variable.

ﬁle_count = 3          # starts with U+FB01 LATIN SMALL LIGATURE FI
print(file_count)
ℌ = 'script H'          # U+210C BLACK-LETTER CAPITAL H  -> 'H'
print(H)
𝐱 = 10                  # U+1D431 MATHEMATICAL BOLD SMALL X  -> 'x'
print(x + 1)
ｙ = 20                  # U+FF59 FULLWIDTH LATIN SMALL LETTER Y -> 'y'
print(y)
µ = 'micro'             # U+00B5 MICRO SIGN -> U+03BC GREEK SMALL LETTER MU
print(μ)
print(sorted(k for k in globals() if k in ('file_count', 'H', 'x', 'y', 'μ')))


def f(ﬁrst, **rest):
    return first, sorted(rest)


print(f(ﬁrst=1, ℌello=2))


class K:
    ﬂag = True          # U+FB02 LATIN SMALL LIGATURE FL


print(K.flag, hasattr(K, 'flag'), 'flag' in K.__dict__)
k = K()
k.ｖalue = 5
print(k.value, vars(k))
ns = {}
exec('ﬁ = 1\nresult = fi + 1', ns)
print(ns['result'], 'fi' in ns)
