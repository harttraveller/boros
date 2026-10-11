# __getattr__, __getattribute__, __setattr__, __delattr__ overrides.

class Dyn:
    def __init__(self):
        self.real = 'real value'

    def __getattr__(self, name):
        if name.startswith('auto_'):
            return name[5:].upper()
        raise AttributeError('%s not found (custom)' % name)


d = Dyn()
print(d.real, d.auto_x, getattr(d, 'auto_yz'))
print(hasattr(d, 'auto_q'), hasattr(d, 'nope'))
try:
    d.nope
except AttributeError as e:
    print('AttributeError:', e)
print(getattr(d, 'nope', 'default'))


# __getattribute__ intercepts everything
class Spy:
    def __init__(self):
        self.log = []
        self.value = 5

    def __getattribute__(self, name):
        if name != 'log':
            object.__getattribute__(self, 'log').append(name)
        return object.__getattribute__(self, name)

    def method(self):
        return 'method called'


s = Spy()
print(s.value, s.method())
print(s.log)
try:
    s.missing
except AttributeError as e:
    print('AttributeError:', e)
print(s.log)


# __getattribute__ raising AttributeError falls back to __getattr__
class Both:
    def __getattribute__(self, name):
        if name == 'hidden':
            raise AttributeError(name)
        return super().__getattribute__(name)

    def __getattr__(self, name):
        return 'getattr:' + name

    x = 1


b = Both()
print(b.x, b.hidden, b.other)


# __setattr__ validation and object.__setattr__ / super().__setattr__
class Strict:
    allowed = ('a', 'b')

    def __init__(self):
        object.__setattr__(self, 'history', [])

    def __setattr__(self, name, value):
        if name not in self.allowed:
            raise AttributeError('cannot set %r' % name)
        self.history.append((name, value))
        super().__setattr__(name, value)

    def __delattr__(self, name):
        self.history.append(('del', name))
        super().__delattr__(name)


st = Strict()
st.a = 1
st.b = 2
try:
    st.c = 3
except AttributeError as e:
    print('AttributeError:', e)
del st.a
print(st.history, hasattr(st, 'a'), st.b)
setattr(st, 'a', 9)
print(st.a, st.history[-1])
try:
    del st.zzz
except AttributeError as e:
    print('AttributeError:', e)


# __setattr__ that stores somewhere else
class Recorder:
    def __init__(self):
        self.__dict__['store'] = {}

    def __setattr__(self, name, value):
        self.store[name] = value

    def __getattr__(self, name):
        try:
            return self.store[name]
        except KeyError:
            raise AttributeError(name) from None


r = Recorder()
r.x = 1
r.y = 2
print(r.x, r.y, r.store, sorted(r.__dict__))


# frozen-style object
class Frozen:
    def __init__(self, v):
        object.__setattr__(self, 'v', v)

    def __setattr__(self, name, value):
        raise TypeError('Frozen is immutable')

    def __delattr__(self, name):
        raise TypeError('Frozen is immutable (del)')


f = Frozen(3)
print(f.v)
for action in ('set', 'del'):
    try:
        if action == 'set':
            f.v = 4
        else:
            del f.v
    except TypeError as e:
        print('TypeError:', e)


# hooks are inherited
class SubDyn(Dyn):
    pass


print(SubDyn().auto_abc)


# __getattr__ is not consulted for attributes that exist
class Counter:
    calls = 0

    def __getattr__(self, name):
        Counter.calls += 1
        return 0


c = Counter()
c.existing = 1
print(c.existing, c.whatever, Counter.calls)


# __getattr__ is not used for special method lookup by operators
class Proxy:
    def __init__(self, target):
        self._target = target

    def __getattr__(self, name):
        return getattr(self._target, name)


px = Proxy([3, 1, 2])
print(px.count(1), px.index(2))
try:
    len(px)
except TypeError as e:
    print('TypeError:', e)


# __getattribute__ defined after class creation
class Late:
    x = 1


late = Late()
print(late.x)
Late.__getattribute__ = lambda self, name: 'intercepted ' + name
print(late.x, late.y)
del Late.__getattribute__
print(late.x)


# __setattr__ added after class creation
def loud_setattr(self, name, value):
    print('setting', name)
    object.__setattr__(self, name, value)

Late.__setattr__ = loud_setattr
late.z = 3
print(late.z)
