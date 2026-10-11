"""close() and throw(GeneratorExit) when the generator *handles*
GeneratorExit: the handler, the code after it and the generator's return
value must behave as in CPython (close() returns the return value in 3.13,
yielding again raises RuntimeError and leaves the generator suspended)."""


# close() returns the generator's return value (3.13+)
def close_returns():
    try:
        yield 1
    except GeneratorExit:
        return 'cleanup-value'


g = close_returns()
next(g)
print('close value ->', g.close())

# swallowing GeneratorExit by yielding again is a RuntimeError; the
# generator stays suspended at the new yield and can be closed again
def stubborn():
    ignored = 0
    while True:
        try:
            yield 'x%d' % ignored
        except GeneratorExit:
            ignored += 1
            print('  ignoring exit', ignored)
            if ignored > 1:
                print('  giving up')
                return 'gave-up'


g = stubborn()
next(g)
try:
    g.close()
except RuntimeError as e:
    print('RuntimeError', e)
print('still suspended:', g.gi_suspended)
print('second close ->', g.close())

# code after an except GeneratorExit handler still runs on close()
def after_handler():
    try:
        yield 1
    except GeneratorExit:
        print('  handler')
    print('  after the try statement')
    return 'final'


g = after_handler()
next(g)
print('close ->', g.close())

# throw(GeneratorExit) is not close(): a value yielded in response is returned
def answer_exit():
    try:
        yield 1
    except GeneratorExit:
        yield 'answered'


g = answer_exit()
next(g)
print('throw GeneratorExit ->', g.throw(GeneratorExit))
g.close()

# GeneratorExit handled inside a loop: the loop body continues after the handler
def loop_handler():
    for i in range(3):
        try:
            yield i
        except GeneratorExit:
            print('  exit at', i)
            break
    print('  after loop')


g = loop_handler()
next(g)
next(g)
print('close ->', g.close())

# handler with finally, then return value
def handler_finally():
    try:
        yield 'a'
    except GeneratorExit:
        print('  except')
        return 'from-except'
    finally:
        print('  finally')


g = handler_finally()
next(g)
print('close ->', g.close())

# bare except also catches GeneratorExit
def bare_except():
    try:
        yield 1
    except:
        print('  bare except caught', 'GeneratorExit')
    yield 'yielded after'


g = bare_except()
next(g)
try:
    g.close()
except RuntimeError as e:
    print('RuntimeError', e)
print(g.gi_suspended)
print(next(g, 'exhausted'))
