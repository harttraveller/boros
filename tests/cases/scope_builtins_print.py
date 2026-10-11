import io
import sys


class R:
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return 'R<%r>' % (self.v,)


class S(R):
    def __str__(self):
        return 'S-str(%s)' % self.v


class Plain:
    pass


print([R(1), R('a')], (R(2),), {'k': R(3)}, {R(4)} if False else '', [S(5)], str([S(6)]))
print(R(7), S(8), str(S(9)), repr(S(10)), f'{S(11)} {S(12)!r} {R(13)}')
print({1: [R(None), (R(()),)]}, [[R([R(0)])]])
print('%s %r' % (S(1), S(2)), '{} {!r}'.format(S(3), R(4)), ascii(R('é')))
print(type(repr(Plain())).__name__, repr(Plain()).startswith('<__main__.Plain object at 0x'))

# print keyword arguments
print('a', 'b', 'c', sep='-')
print('a', 'b', sep='')
print('x', end='')
print('y', end='!\n')
print()
print(sep='never shown')
print('multi', 1, 2.5, None, True, sep=', ', end=' <end>\n')
print(*[1, 2, 3], sep=' | ')
print('flushed', flush=True)
buf = io.StringIO()
print('to', 'buffer', sep='_', end='$', file=buf)
print(R(1), file=buf)
print(repr(buf.getvalue()))
print('to stderr', file=sys.stderr)
print('to stderr flushed', file=sys.stderr, flush=True)
sys.stdout.write('direct write\n')
print(None, file=None)


class Writer:
    def __init__(self):
        self.parts = []

    def write(self, s):
        self.parts.append(s)

    def flush(self):
        self.parts.append('<flush>')


w = Writer()
print('a', 'b', file=w, flush=True)
print(w.parts)
try:
    print('x', sep=5)
except TypeError as e:
    print('TypeError:', e)
try:
    print('x', end=[])
except TypeError as e:
    print('TypeError:', e)


class BadRepr:
    def __repr__(self):
        return 42


try:
    print([BadRepr()])
except TypeError as e:
    print('TypeError:', e)
