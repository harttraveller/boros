"""Semantic version handling: a Version class completed with
functools.total_ordering, parsing with a regex, sorting, bisect lookups,
range constraints, and a tiny dependency resolver."""
import bisect
import functools
import re

VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.]+))?$")


@functools.total_ordering
class Version:
    __slots__ = ("major", "minor", "patch", "pre")

    def __init__(self, text):
        m = VERSION_RE.match(text)
        if not m:
            raise ValueError("invalid version %r" % text)
        self.major, self.minor, self.patch = int(m[1]), int(m[2]), int(m[3])
        self.pre = tuple(int(p) if p.isdigit() else p for p in m[4].split(".")) if m[4] else ()

    def key(self):
        # a release sorts after all of its pre-releases
        return (self.major, self.minor, self.patch, not self.pre, self.pre)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.key() == other.key()

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.key() < other.key()

    def __hash__(self):
        return hash(self.key())

    def __repr__(self):
        s = "%d.%d.%d" % (self.major, self.minor, self.patch)
        return s + ("-" + ".".join(map(str, self.pre)) if self.pre else "")

    def bump(self, part):
        parts = [self.major, self.minor, self.patch]
        i = ["major", "minor", "patch"].index(part)
        parts[i] += 1
        parts[i + 1:] = [0] * (2 - i)
        return Version("%d.%d.%d" % tuple(parts))


class Constraint:
    OPS = {">=": lambda a, b: a >= b, "<": lambda a, b: a < b, "==": lambda a, b: a == b,
           ">": lambda a, b: a > b, "<=": lambda a, b: a <= b, "!=": lambda a, b: a != b}

    def __init__(self, spec):
        self.parts = []
        for piece in spec.split(","):
            m = re.match(r"\s*(>=|<=|==|!=|<|>)\s*(\S+)\s*$", piece)
            if not m:
                raise ValueError("bad constraint %r" % piece)
            self.parts.append((m[1], Version(m[2])))

    def __contains__(self, v):
        return all(self.OPS[op](v, bound) for op, bound in self.parts)


AVAILABLE = {
    "app": ["1.0.0", "1.1.0", "2.0.0-rc.1", "2.0.0"],
    "lib": ["0.9.0", "1.0.0-alpha", "1.0.0-alpha.2", "1.0.0-beta", "1.0.0", "1.2.3", "2.0.0"],
    "util": ["3.1.4", "3.2.0", "4.0.0"],
}
DEPS = {
    ("app", "2.0.0"): {"lib": ">=1.0.0, <2.0.0", "util": ">=3.2.0"},
    ("app", "1.1.0"): {"lib": ">=0.9.0"},
    ("lib", "1.2.3"): {"util": "<4.0.0"},
}


def resolve(name, spec, chosen=None, depth=0):
    chosen = {} if chosen is None else chosen
    cons = Constraint(spec)
    candidates = sorted((Version(v) for v in AVAILABLE[name]), reverse=True)
    for v in candidates:
        if v.pre or v not in cons:
            continue
        if name in chosen and chosen[name] != v:
            continue
        trial = dict(chosen, **{name: v})
        try:
            for dep, dspec in DEPS.get((name, repr(v)), {}).items():
                trial = resolve(dep, dspec, trial, depth + 1)
            return trial
        except LookupError:
            continue
    raise LookupError("no version of %s satisfies %r" % (name, spec))


versions = [Version(v) for v in AVAILABLE["lib"]]
shuffled = versions[3:] + versions[:3]
print(sorted(shuffled))
print(min(versions), max(versions), Version("1.0.0") > Version("1.0.0-beta"), Version("1.0.0-alpha") <= Version("1.0.0-alpha.2"))
print(Version("1.2.3") >= Version("1.2.3"), Version("0.1.0") != Version("0.1.0"), Version("2.0.0") > Version("10.0.0"))
print(Version("1.9.9").bump("minor"), Version("1.9.9").bump("major"), Version("1.9.9").bump("patch"))
print(len({Version("1.0.0"), Version("1.0.0"), Version("1.0.1")}))
idx = bisect.bisect_left(versions, Version("1.0.0"))
print(idx, versions[idx], bisect.bisect_right(versions, Version("1.1.0")))
for spec in (">=1.0.0, <2.0.0", "==1.0.0", "!=1.2.3, >0.9.0", "<1.0.0"):
    c = Constraint(spec)
    print("%-18s %s" % (spec, [v for v in versions if v in c]))
print(resolve("app", ">=1.0.0"))
print(resolve("app", "<2.0.0"))
for bad in (lambda: Version("1.2"), lambda: Constraint("~1.0"), lambda: resolve("util", ">5.0.0"),
            lambda: Version("1.0.0") < "1.0.1"):
    try:
        bad()
    except (ValueError, LookupError, TypeError) as e:
        print(type(e).__name__ + ":", e)
