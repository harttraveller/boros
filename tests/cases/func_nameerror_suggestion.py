# An uncaught NameError for a misspelled name ends with CPython's
# "Did you mean" suggestion, computed from the failing frame's locals,
# the globals and the builtins.
counter = 0


def bump(amount):
    total_amount = amount + 1
    return total_amonut * 2


print('start')
bump(1)
