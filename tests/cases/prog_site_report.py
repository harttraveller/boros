"""Site report generator built by subclassing standard-library classes the
way applications usually do (template-method overrides): HTMLParser for
link/heading extraction, json.JSONEncoder.default for custom types,
logging.Handler.emit to capture log records, threading.Thread.run workers,
a dict subclass with __missing__, and an attribute-access dict. Each
section is independent so one failure does not hide the others."""
import json
import logging
import threading
from collections import Counter
from html.parser import HTMLParser

PAGES = {
    "index.html": '<html><h1>Home</h1><p>Welcome <a href="about.html">about</a> and '
                  '<a href="blog.html" class="nav">blog</a>.</p></html>',
    "about.html": "<h1>About us</h1><p>We write <b>interpreters</b>. <a href='index.html'>home</a></p>",
    "blog.html": "<h1>Blog</h1><h2>First post</h2><p>Hello &amp; welcome</p><a href=missing.html>?</a>",
}


def section(name):
    def deco(fn):
        try:
            print(name + ":", fn())
        except Exception as e:
            print(name + ": raised", type(e).__name__, e)
        return fn
    return deco


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.headings = []
        self.words = Counter()
        self._in_heading = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href"))
        elif tag in ("h1", "h2"):
            self._in_heading = tag

    def handle_endtag(self, tag):
        if tag == self._in_heading:
            self._in_heading = None

    def handle_data(self, data):
        if self._in_heading:
            self.headings.append((self._in_heading, data.strip()))
        self.words.update(w.lower().strip(".&?") for w in data.split() if w.strip(".&?"))


class Page:
    def __init__(self, name, links, headings, words):
        self.name, self.links, self.headings, self.words = name, links, headings, words


class ReportEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Page):
            return {"page": o.name, "links": o.links, "top": o.words.most_common(2)}
        if isinstance(o, (set, frozenset)):
            return sorted(o)
        return super().default(o)


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))


class ParseWorker(threading.Thread):
    def __init__(self, name, html):
        super().__init__(name="worker-" + name)
        self.page_name = name
        self.html = html
        self.page = None

    def run(self):
        p = PageParser()
        p.feed(self.html)
        p.close()
        self.page = Page(self.page_name, p.links, p.headings, p.words)


class LinkIndex(dict):
    def __missing__(self, key):
        value = self[key] = set()
        return value


class AttrDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


@section("parser")
def _():
    p = PageParser()
    p.feed(PAGES["blog.html"])
    return p.links, p.headings, sorted(p.words.items())


@section("encoder")
def _():
    page = Page("x", ["a"], [], Counter("aab"))
    return json.dumps({"p": page, "s": {3, 1, 2}}, cls=ReportEncoder, sort_keys=True)


@section("encoder fallback")
def _():
    return json.dumps(object(), cls=ReportEncoder)


@section("logging")
def _():
    log = logging.getLogger("site-report")
    log.propagate = False
    h = ListHandler()
    h.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    log.addHandler(h)
    log.setLevel(logging.DEBUG)
    log.debug("not captured")
    log.info("parsed %d pages", 3)
    log.warning("broken link %s", "missing.html")
    log.removeHandler(h)
    return h.records


@section("threads")
def _():
    workers = [ParseWorker(name, html) for name, html in sorted(PAGES.items())]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    return [(w.name, w.page.name if w.page else None, w.page.links if w.page else None) for w in workers]


@section("missing")
def _():
    idx = LinkIndex()
    for src, dst in [("a", "b"), ("a", "c"), ("b", "a")]:
        idx[dst].add(src)
    return sorted((k, sorted(v)) for k, v in idx.items()), "zz" in idx


@section("attrdict")
def _():
    cfg = AttrDict(depth=2)
    cfg.verbose = True
    return cfg.depth, cfg["verbose"], sorted(cfg)


@section("full report")
def _():
    pages = []
    for name, html in sorted(PAGES.items()):
        p = PageParser()
        p.feed(html)
        pages.append(Page(name, p.links, p.headings, p.words))
    known = {p.name for p in pages}
    broken = sorted({l for p in pages for l in p.links if l not in known})
    return json.dumps({"pages": pages, "broken": broken}, cls=ReportEncoder)
