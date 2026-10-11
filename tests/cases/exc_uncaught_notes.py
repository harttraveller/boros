# add_note(): notes are visible in __notes__ and printed after the exception line.


class Annotated(Exception):
    pass


e = Annotated('with notes')
e.add_note('first note')
e.add_note('second note')
print(e.__notes__)

h = ValueError('host with notes')
h.add_note('host note')
print(h.__notes__)

try:
    e.add_note(5)
except TypeError as t:
    print('TypeError:', t)


def fail():
    try:
        raise Annotated('uncaught')
    except Annotated as err:
        err.add_note('context: while failing')
        raise


fail()
