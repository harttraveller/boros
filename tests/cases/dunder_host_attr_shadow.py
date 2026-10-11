# Host code (operator.attrgetter, str.format field lookup) reading
# attributes of interpreted instances whose names collide with names the
# interpreter's own instance representation defines (cls, d, native, sv,
# __class__).
import operator


def show(label, f):
    try:
        print(label, '->', f())
    except Exception as e:
        print(label, '->', type(e).__name__ + ':', e)


class Rec:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def __repr__(self):
        return 'Rec(%s)' % ', '.join('%s=%r' % kv for kv in sorted(vars(self).items()))


r = Rec(d=4, cls='c', native=1, sv='s')
show('attrgetter d', lambda: operator.attrgetter('d')(r))
show('attrgetter cls', lambda: operator.attrgetter('cls')(r))
show('attrgetter native', lambda: operator.attrgetter('native')(r))
show('attrgetter sv', lambda: operator.attrgetter('sv')(r))
show('sorted by attrgetter d', lambda: sorted([Rec(d=3), Rec(d=1), Rec(d=2)], key=operator.attrgetter('d')))
show('format d', lambda: '{0.d}'.format(r))
show('format cls', lambda: '{r.cls}'.format(r=r))
show('format __class__', lambda: '{0.__class__.__name__}'.format(r))
show('attrgetter __class__', lambda: operator.attrgetter('__class__')(r).__name__)
