# An uncaught NameError for a standard-library module name suggests the
# missing import.


def area(r):
    return math.pi * r * r


print('before')
print(area(2))
