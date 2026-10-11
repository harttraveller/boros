# Host (stdlib) base classes whose own methods call methods that the
# interpreted subclass overrides ("template method" pattern), or that set
# instance attributes in their __init__.
import collections
import html.parser
import logging
import string
import threading


# 1. threading.Thread.start() calls self.run()
class Worker(threading.Thread):
    def __init__(self, n):
        super().__init__()
        self.n = n
        self.result = None

    def run(self):
        self.result = sum(range(self.n))


w = Worker(10)
w.start()
w.join()
print('1', w.result)


# 2. HTMLParser.feed() calls self.handle_starttag() / handle_data()
class TagCollector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, attrs))

    def handle_data(self, data):
        if data.strip():
            self.tags.append(('data', data.strip()))


tc = TagCollector()
tc.feed('<p class="x">hi <b>there</b></p>')
print('2', tc.tags)


# 3. attributes set by a host base __init__ are visible on the instance
class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records = []

    def emit(self, record):
        self.records.append(record.getMessage())


h = ListHandler()
try:
    print('3', h.level, h.filters)
except AttributeError as e:
    print('3 AttributeError:', e)

# 4. logging.Handler.handle() calls self.emit()
log = logging.getLogger('scope_case')
log.propagate = False
log.addHandler(h)
try:
    log.warning('careful %d', 1)
    log.error('bad')
    print('4', h.records)
except AttributeError as e:
    print('4 AttributeError:', e)


# 5. string.Formatter.format() calls self.format_field()
class Shout(string.Formatter):
    def format_field(self, value, spec):
        return str(value).upper()


print('5', Shout().format('{0} and {1}', 'a', 'b'))


# 6. collections.UserDict.__getitem__ calls self.__missing__
class Defaulting(collections.UserDict):
    def __missing__(self, key):
        return 'missing:' + key


try:
    ud = Defaulting(a=1)
    print('6', ud['a'], ud['zz'], len(ud), sorted(ud))
except Exception as e:
    print('6', type(e).__name__, e)
