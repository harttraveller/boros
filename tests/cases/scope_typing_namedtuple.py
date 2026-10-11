from typing import NamedTuple


class Emp(NamedTuple):
    name: str
    dept: str = 'eng'

    def tag(self):
        return '%s@%s' % (self.name, self.dept)


e = Emp('ann')
print(e, e.tag(), e._fields, e._asdict(), Emp('bob', 'ops').dept)
