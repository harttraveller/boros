# A class body that uses locals(), vars(), exec() or eval() still behaves
# like any other class body: its methods can use zero-argument super() and
# free variables, and the names it adds become class attributes.


class Base:
    def hello(self):
        return 'base'


def make(tag):
    class K(Base):
        x = tag
        locals()['y'] = tag * 2
        exec('z = x + "!"')
        w = eval('x + y')
        seen = sorted(k for k in locals() if not k.startswith('__'))

        def hello(self):
            return super().hello() + '/' + tag
    return K


K = make('t')
print(K.x, K.y, K.z, K.w, K.seen, K().hello())
print(sorted(k for k in vars(K) if not k.startswith('__')))
print(type(K.__dict__).__name__, K.__qualname__, '__qualname__' in K.__dict__)


class Plain:
    names = dir()
    count = len(locals())


print([n for n in Plain.names if not n.startswith('__')], Plain.count > 0)
