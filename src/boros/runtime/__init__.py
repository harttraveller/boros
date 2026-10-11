"""The runtime: the object model that interpreted programs run on.

Interpreted values are host objects.  Most are the host's own (ints,
strings, lists, ...); functions, classes and instances defined by the
interpreted program are represented by the classes in `objects`.  The
modules, roughly from the bottom up:

    objects            Function, Method, Class, Instance, Super, signals
    lookup             attribute lookup along a class's MRO, cached and classified
    errors             traceback recording and host-exception helpers
    coroutines         generator, coroutine and async generator objects
    calls              argument binding, function invocation, instantiation
    attributes         getting, setting and deleting attributes
    typechecks         isinstance(), issubclass() and callable()
    protocols          special methods: host operations forwarded to interpreted classes
    object_methods     emulations of the methods of `object`
    classes            the class statement and type()
    exceptions         raising, matching and printing exceptions
    tracebacks         the traceback module of interpreted programs
    builtin_functions  the builtins namespace of interpreted programs
    modules            the import system

Importing this package loads every runtime module, which also installs the
special-method forwarding on Instance and the `object` method emulations.
Two more are loaded only when first needed: introspection (__signature__,
__closure__ and co_* of interpreted functions) and host_overrides (the
versions of host library functions that understand interpreted classes).
"""

from __future__ import annotations

from . import (
    attributes,
    builtin_functions,
    calls,
    classes,
    errors,
    exceptions,
    lookup,
    modules,
    object_methods,
    objects,
    protocols,
    tracebacks,
    typechecks,
)

__all__: list[str] = ['attributes', 'builtin_functions', 'calls', 'classes', 'errors', 'exceptions', 'lookup',
                      'modules', 'object_methods', 'objects', 'protocols', 'tracebacks', 'typechecks']
