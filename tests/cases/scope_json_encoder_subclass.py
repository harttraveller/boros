import json


class Money:
    def __init__(self, cents):
        self.cents = cents


class MoneyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Money):
            return '%d.%02d' % divmod(o.cents, 100)
        return super().default(o)


try:
    print('1', json.dumps({'price': Money(1234)}, cls=MoneyEncoder))
except TypeError as e:
    print('1 TypeError:', e)
try:
    print('2', MoneyEncoder(indent=None).encode([Money(5)]))
except TypeError as e:
    print('2 TypeError:', e)
try:
    json.dumps(object(), cls=MoneyEncoder)
except TypeError as e:
    print('3 TypeError:', str(e).split(' is not')[0][:9], 'is not' in str(e))


class Decoder(json.JSONDecoder):
    def __init__(self, **kw):
        super().__init__(object_hook=self.hook, **kw)

    def hook(self, d):
        return sorted(d)


print('4', json.loads('{"b": 1, "a": 2}', cls=Decoder))
