"""Invoice/report rendering: str.format with the full format-spec mini
language (fill, align, sign, width, grouping, precision, types), nested
f-string specs, __format__ overrides on a Money class, format() builtin,
string.Template, textwrap, str methods (center/ljust/partition/translate),
and locale-free number formatting."""
import string
import textwrap
from decimal import Decimal, ROUND_HALF_UP


class Money:
    def __init__(self, amount, currency="EUR"):
        self.amount = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.currency = currency

    def __add__(self, other):
        if isinstance(other, int) and other == 0:
            return self
        if not isinstance(other, Money) or other.currency != self.currency:
            return NotImplemented
        return Money(self.amount + other.amount, self.currency)

    __radd__ = __add__

    def __mul__(self, k):
        return Money(self.amount * Decimal(str(k)), self.currency)

    def __format__(self, spec):
        # "c" suffix => with currency code; the rest is a Decimal spec
        with_code = spec.endswith("c")
        if with_code:
            spec = spec[:-1]
        text = format(self.amount, spec or ",.2f")
        return "%s %s" % (text, self.currency) if with_code else text

    def __repr__(self):
        return "Money(%r, %r)" % (str(self.amount), self.currency)

    def __str__(self):
        return format(self, "c")


LINES = [
    ("Widget, large", 3, Money("19.99")),
    ("Gizmo", 12, Money("4.5")),
    ("Consulting (hours)", 7.5, Money("120")),
    ("Discount coupon", 1, Money("-25")),
]
WIDTH = 60


def render(customer, lines, tax_rate=0.21):
    out = []
    out.append("=" * WIDTH)
    out.append("{:^{w}}".format("INVOICE", w=WIDTH))
    out.append("{0:<{1}}{2:>{3}}".format("Customer: " + customer, WIDTH // 2, "No. 2024-0042", WIDTH - WIDTH // 2))
    out.append("-" * WIDTH)
    header = f"{'Item':<28}{'Qty':>6}{'Price':>12}{'Total':>14}"
    out.append(header)
    subtotal = 0
    for name, qty, price in lines:
        total = price * qty
        subtotal = subtotal + total
        qty_s = f"{qty:>6g}" if isinstance(qty, float) else f"{qty:>6d}"
        out.append(f"{name[:27]:<28}{qty_s}{price:>12}{total:>14,.2f}")
    tax = subtotal * tax_rate
    out.append("-" * WIDTH)
    for label, value in (("Subtotal", subtotal), ("VAT {:.0%}".format(tax_rate), tax), ("TOTAL", subtotal + tax)):
        out.append(f"{label:>46}{value:>14c}" if label == "TOTAL" else f"{label:>46}{value:>14}")
    out.append("=" * WIDTH)
    return "\n".join(out), subtotal + tax


text, grand = render("ACME Corp.", LINES)
print(text)
print(repr(grand), str(grand), f"{grand!r:>40}", f"{grand!s:*^30}")

# format-spec mini language
n = 1234567.891
print("{:,}|{:_}|{:+.2e}|{:010.3f}|{:x}|{:#o}|{:#b}|{:%}".format(n, 1000000, n, -3.14159, 255, 8, 5, 0.256))
print("{:>8}|{:<8}|{:^8}|{:*>8}|{:=+8d}|{: d}|{:c}".format("r", "l", "c", "f", 42, 7, 65))
print(f"{3.0:g}|{1e20:g}|{1.5e-7:g}|{123.456:.2g}|{0.0001234:.3e}|{float('inf'):f}|{-0.0:+}")
print(format(12345, "08,d"), format(-42, "^9"), format("abc", ".2"), format(Decimal("1.005"), ".2f"), format(True, "d"))
width, prec = 12, 3
print(f"[{n:{width}.{prec}f}] [{'x':{'>'}{width}}] [{n!r:.6}]")
print("%-10s|%5.1f|%+d|%05d|%x|%r|%%|%c" % ("pct", 3.14159, 5, 42, 255, "q", 66))
print("%(name)s is %(age)d" % {"name": "Ada", "age": 36}, "%s" % ((1, 2),), "%.3s" % "abcdef")

# templates and text utilities
tmpl = string.Template("Dear $name, your balance is ${amount}. $$5 fee applies.")
print(tmpl.substitute(name="Bob", amount=grand))
print(tmpl.safe_substitute(name="Eve"))
try:
    tmpl.substitute(name="X")
except KeyError as e:
    print("KeyError", e)
para = ("Boros interprets Python source by compiling each syntax tree node into a closure; "
        "the closures call each other to run the program, which is fast enough to run itself.")
print(textwrap.fill(para, width=40, initial_indent="  ", subsequent_indent="    "))
print(textwrap.shorten(para, width=50, placeholder=" [...]"), textwrap.dedent("   a\n    b\n   c").split("\n"))
print("Total".center(11, "."), "id".ljust(5, "_"), "7".zfill(4), "a,b,,c".split(","), "k=v=w".partition("="))
table = str.maketrans({"a": "4", "e": "3", "o": None})
print("hello boros".translate(table), "Title Case Words".swapcase(), "x".join("abc"), "  pad  ".strip(), "%s" % None)
print(sorted(string.Formatter().parse("a{0}b{name!r:>5}c")), string.capwords("hello   wide world"))
