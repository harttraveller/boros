# Attributes that host code stores on the exception object (add_note,
# traceback machinery) are visible on instances of user exception classes.

class AppError(Exception):
    pass


e = AppError('noted')
e.add_note('first note')
e.add_note('second note')
print(e.__notes__)
print(hasattr(e, '__notes__'), getattr(e, '__notes__', None))

try:
    raise AppError('with traceback')
except AppError as err:
    print(type(err.__traceback__).__name__, err.__traceback__ is not None)

plain = ValueError('plain')
plain.add_note('host note')
print(plain.__notes__)
