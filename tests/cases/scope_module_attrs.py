"""Docstring of the main script."""
import sys
import _scope_attrs

# module docstrings become __doc__
print(repr(__doc__))
print(repr(_scope_attrs.__doc__), repr(_scope_attrs.doc_seen_inside))
d = {}
exec('"exec docstring"\nx = 1', d)
print(repr(d.get('__doc__')), d['x'])
