# Exception subclass with __new__ calling the host base __new__ explicitly.


class WithNew(Exception):
    def __new__(cls, *args):
        self = Exception.__new__(cls, *args)
        self.created = True
        return self


w = WithNew('n')
print(w.args, w.created, isinstance(w, WithNew))


class ViaSuper(ValueError):
    def __new__(cls, *args):
        self = super().__new__(cls, *args)
        self.tag = 'super'
        return self


v = ViaSuper('s')
print(v.args, v.tag, isinstance(v, ValueError), str(v), repr(v))
