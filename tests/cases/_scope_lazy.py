# PEP 562: module-level __getattr__ and __dir__
eager = 'eager'
_loaded = []


def __getattr__(name):
    if name.startswith('lazy_'):
        _loaded.append(name)
        return name[5:].upper()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return ['eager', 'lazy_x']
