"""Module docstring.

    Indented second paragraph.
"""
# Python 3.13 strips the common leading indentation from docstrings at
# compile time (like inspect.cleandoc, but keeping blank lines).

print(repr(__doc__))


def f():
    """Docstring with "quotes" and 'apostrophes'.

    Second paragraph \\ with backslash.
        Deeper indented line.
    """
    return 1


def g():
    """   single line with leading spaces"""


def h():
    '''
    starts on the second line
      more
    '''


def no_doc():
    x = 1
    """not a docstring"""
    return x


def concat_doc():
    "concatenated " 'docstring'


class C:
    """Class docstring.

    Details here.
    """

    def method(self):
        """Method doc.

        More.
        """


def tabbed():
	"""Tab indented.

	Second line.
	"""


print(repr(f.__doc__))
print(repr(g.__doc__))
print(repr(h.__doc__))
print(repr(no_doc.__doc__))
print(repr(concat_doc.__doc__))
print(repr(C.__doc__))
print(repr(C.method.__doc__))
print(repr(C().method.__doc__))
print(repr(tabbed.__doc__))
print(repr((lambda: 1).__doc__))
ns = {}
exec('def k():\n    """A.\n\n    B.\n    """\n', ns)
print(repr(ns['k'].__doc__))
