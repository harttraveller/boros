# Uncaught exception whose __str__ raises: the final line is "Name: <exception str() failed>".


class Broken(Exception):
    def __str__(self):
        raise ValueError('str is broken')


print('raising Broken')
raise Broken('x')
