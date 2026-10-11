"""Helper module for prog_plugins.py: defines a plugin class at import time
through a factory so that it registers into the main program's registry."""

LOADED = []


def register(registry, base):
    class Shout(base, name="shout"):
        def run(self, text):
            return text.upper() + "!" * self.level

    LOADED.append(Shout)
    return Shout


def describe(cls):
    return "%s from %s (%s)" % (cls.__qualname__, __name__, cls.__module__)
