# The traceback module applied to interpreted exceptions (only the exception
# lines are compared; frame lines depend on the implementation).
import io
import traceback


class MyErr(Exception):
    pass


class Pretty(ValueError):
    def __str__(self):
        return 'pretty message'


def last(lines):
    return [ln for ln in ''.join(lines).splitlines() if ln.strip()][-1]


for exc in (MyErr('boom'), Pretty('ignored'), KeyError('k'), MyErr()):
    print(traceback.format_exception_only(exc))
    print(traceback.format_exception_only(type(exc), exc))
    print(last(traceback.format_exception(exc)))

try:
    raise MyErr('caught one')
except MyErr:
    print(last([traceback.format_exc()]))
    buf = io.StringIO()
    traceback.print_exc(file=buf)
    print(last([buf.getvalue()]))

try:
    try:
        raise MyErr('inner')
    except MyErr as inner:
        raise Pretty('outer') from inner
except Pretty as e:
    text = ''.join(traceback.format_exception(e))
    print('direct cause' in text, last([text]))
    print(traceback.format_exception_only(e.__cause__))
