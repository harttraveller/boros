import operator


class Rec:
    def __init__(self):
        self.d = 'd-attr'
        self.cls = 'cls-attr'
        self.native = 'native-attr'
        self.sv = 'sv-attr'
        self.plain = 'plain-attr'


r = Rec()
# host code (operator, str.format) reading attributes of interpreted objects
print('1', operator.attrgetter('plain')(r), '{0.plain}'.format(r))
print('2', operator.attrgetter('d', 'cls')(r))
print('3', operator.attrgetter('native', 'sv')(r))
print('4', '{0.d} {0.cls}'.format(r))
print('5', sorted([r], key=operator.attrgetter('d'))[0] is r)
