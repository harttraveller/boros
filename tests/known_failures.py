"""Test cases that boros does not pass yet, with the reason.

They are run as strict expected failures: if one starts passing, the test
run reports it, and it should be removed from here.
"""

from __future__ import annotations

HOST_TYPES: str = ('host C code that checks exact host types (str.join, json, unittest.assertRaises, '
                   'singledispatch.register, asyncio results) would need a real host class per interpreted class')
HOST_MESSAGES: str = ('error messages produced by CPython itself name the reflected operation or the host type '
                      "'Instance' instead of the interpreted class")
HOST_ATTRS: str = ("host attribute reads (operator.attrgetter, str.format) see the interpreter's own Instance "
                   'fields cls, d, native and sv')
FUNC_ATTRS: str = 'deleting __name__ and assigning a non-dict __dict__ on functions are not validated like CPython'

INNER_SETATTR: str = ('level 2: host code (functools.wraps, update_wrapper, abc) setting attributes on the inner '
                      "interpreter's objects bypasses the interpreted properties that hold them")
INNER_HOST_CLASSES: str = ('level 2: subclasses of pure-Python host classes need a host shadow class, which an '
                           'interpreted type() cannot create')
INNER_DETAILS: str = 'level 2: host introspection of the inner interpreter (annotations, finalizers, abc checks)'

LEVEL1: dict[str, str] = {
    'class_bug_builtin_subclass_hostcode': HOST_TYPES,
    'gen_async_user_exceptions': HOST_TYPES,
    'prog_async_jobs': HOST_TYPES,
    'prog_unittest_suite': HOST_TYPES,
    'scope_functools_singledispatch': HOST_TYPES,
    'scope_namedtuple_subclass': HOST_TYPES,
    'dunder_opmsg_hostleft': HOST_MESSAGES,
    'dunder_typename_leak': HOST_MESSAGES,
    'expr_compare_reflected_msg': HOST_MESSAGES,
    'dunder_host_attr_shadow': HOST_ATTRS,
    'scope_host_attr_access': HOST_ATTRS,
    'func_attr_validation': FUNC_ATTRS,
}
"""Cases that fail when boros runs them (level 1)."""

LEVEL2: dict[str, str] = {
    **LEVEL1,
    'class_bug_host_reads_doc': INNER_SETATTR,
    'class_functools_wraps': INNER_SETATTR,
    'dunder_host_attrs': INNER_SETATTR,
    'func_dict': INNER_SETATTR,
    'func_host_doc_lookup': INNER_SETATTR,
    'func_wraps': INNER_SETATTR,
    'prog_level2_interop': INNER_SETATTR,
    'prog_lru_cache': INNER_SETATTR,
    'prog_plugins': INNER_SETATTR,
    'scope_stdlib_functools': INNER_SETATTR,
    'prog_abc_collections': INNER_HOST_CLASSES,
    'prog_site_report': INNER_HOST_CLASSES,
    'scope_host_template_methods': INNER_HOST_CLASSES,
    'scope_json_encoder_subclass': INNER_HOST_CLASSES,
    'dunder_hash': INNER_DETAILS,
    'func_annotations': INNER_DETAILS,
    'gen_async_generator_finalize': INNER_DETAILS,
}
"""Cases that fail when boros runs boros running them (level 2)."""
