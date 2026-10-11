# Statements with several expression parts inside generators: an assert's
# message is only evaluated when the test fails, and `raise X from Y`
# evaluates X before Y, even when one part contains yield.
log = []


def v(x):
    log.append(x)
    return x


def g1():
    assert v(True), (yield "msg")
    yield "after assert"


print(list(g1()), log)
log.clear()


def g2():
    try:
        raise v(ValueError("x")) from (yield "cause")
    except ValueError as e:
        yield ("caught", type(e.__cause__).__name__)


gen = g2()
print(next(gen), log)
print(gen.send(KeyError("k")), log)
