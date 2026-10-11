"""Regex-based log analyzer: named groups, verbose patterns, re.sub with a
function, Counter/defaultdict aggregation, itertools.groupby, sorting with
multiple keys, string formatting with alignment, and a report generator."""
import re
from collections import Counter, defaultdict, OrderedDict
from itertools import groupby
from operator import itemgetter, attrgetter

LOG = """\
2024-03-01 10:00:01 INFO  [web] GET /index.html 200 12ms user=alice
2024-03-01 10:00:02 INFO  [web] GET /about.html 200 8ms user=bob
2024-03-01 10:00:05 WARN  [db] slow query took 1532ms table=orders
2024-03-01 10:01:00 ERROR [web] GET /api/orders 500 230ms user=alice err="Timeout: db"
2024-03-01 10:01:30 INFO  [web] POST /api/orders 201 45ms user=carol
garbage line that does not match
2024-03-01 10:02:10 DEBUG [cache] miss key=user:42
2024-03-01 10:02:11 INFO  [web] GET /index.html 304 2ms user=bob
2024-03-02 09:15:00 ERROR [db] connection reset peer=10.0.0.7:5432
2024-03-02 09:15:01 WARN  [web] GET /api/orders 503 1ms user=dave err="Service Unavailable"
2024-03-02 09:16:45 INFO  [web] GET /index.html 200 15ms user=alice
2024-03-02 11:00:00 INFO  [auth] login ok user=erin ip=192.168.1.20
2024-03-02 11:00:03 ERROR [auth] login failed user=mallory ip=203.0.113.9
2024-03-02 11:00:04 ERROR [auth] login failed user=mallory ip=203.0.113.9
"""

LINE = re.compile(r"""
    ^(?P<date>\d{4}-\d{2}-\d{2})\s
    (?P<time>\d{2}:\d{2}:\d{2})\s+
    (?P<level>[A-Z]+)\s+
    \[(?P<comp>\w+)\]\s
    (?P<msg>.*)$
""", re.VERBOSE)
REQUEST = re.compile(r"(?P<method>GET|POST|PUT|DELETE) (?P<path>\S+) (?P<status>\d{3}) (?P<ms>\d+)ms")
KV = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')
IP = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")
LEVELS = OrderedDict((name, i) for i, name in enumerate(["DEBUG", "INFO", "WARN", "ERROR"]))


class Entry:
    __slots__ = ("date", "time", "level", "comp", "msg", "fields", "request")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def severity(self):
        return LEVELS[self.level]

    def __repr__(self):
        return "<%s %s %s>" % (self.level, self.comp, self.msg[:20])


def parse(text):
    entries, bad = [], []
    for lineno, line in enumerate(text.splitlines(), 1):
        m = LINE.match(line)
        if not m:
            bad.append(lineno)
            continue
        d = m.groupdict()
        fields = {k: v.strip('"') for k, v in KV.findall(d["msg"])}
        rq = REQUEST.search(d["msg"])
        e = Entry(fields=fields, request=rq.groupdict() if rq else None, **d)
        entries.append(e)
    return entries, bad


def mask_ip(m):
    a, b, c, d = m.groups()
    return "%s.%s.x.x" % (a, b)


entries, bad = parse(LOG)
print("parsed", len(entries), "bad lines", bad)
print(Counter(e.level for e in entries).most_common())
print(sorted(Counter(e.comp for e in entries).items(), key=lambda kv: (-kv[1], kv[0])))

by_day = groupby(entries, key=attrgetter("date"))
for day, group in by_day:
    group = list(group)
    worst = max(group, key=lambda e: (e.severity, e.time))
    print(day, len(group), "worst:", worst.level, worst.time, worst)

reqs = [e.request for e in entries if e.request]
stat = defaultdict(lambda: {"n": 0, "ms": 0, "codes": Counter()})
for r in reqs:
    s = stat[(r["method"], r["path"])]
    s["n"] += 1
    s["ms"] += int(r["ms"])
    s["codes"][r["status"]] += 1
print("%-6s %-16s %3s %7s  %s" % ("method", "path", "n", "avg_ms", "codes"))
for (method, path), s in sorted(stat.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
    print("%-6s %-16s %3d %7.1f  %s" % (method, path, s["n"], s["ms"] / s["n"], dict(sorted(s["codes"].items()))))

errors = [e for e in entries if e.severity >= LEVELS["WARN"]]
for e in sorted(errors, key=lambda e: (-e.severity, e.date, e.time)):
    print("{0.level:<5}|{0.comp:^7}|{1}".format(e, IP.sub(mask_ip, e.msg)))

users = Counter(e.fields["user"] for e in entries if "user" in e.fields)
print("users:", ", ".join("%s=%d" % kv for kv in sorted(users.items(), key=itemgetter(0))))
failed = Counter((e.fields["user"], e.fields["ip"]) for e in entries if "failed" in e.msg)
for (user, ip), n in failed.items():
    if n >= 2:
        print("ALERT: %d failed logins for %s from %s" % (n, user, IP.sub(r"\1.\2.\3.***", ip)))

errs = {e.fields.get("err") for e in entries if "err" in e.fields}
print(sorted(errs), re.findall(r"\d+ms", LOG)[:4], re.split(r"[\s/=]+", "GET /api/orders user=alice", maxsplit=3))
tmpl = re.sub(r"\{(\w+)\}", lambda m: str(len(m.group(1))), "a{bb}c{dddd}e{}")
print(tmpl, re.escape("1.5+2"), bool(re.fullmatch(r"[a-z]+\d*", "abc123")), re.match(r"(a)(b)?", "ac").groups())
m = re.search(r"(?P<h>\d\d):(?P<m>\d\d)", "at 10:45 today")
print(m.span(), m.group("h", "m"), m.start("m"), m.expand(r"\g<m>/\g<h>"), m.re.pattern, m.lastgroup)
try:
    re.compile(r"(unclosed")
except re.error as e:
    print("re.error:", e.msg, "at", e.pos)
