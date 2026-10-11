# Arithmetic edge cases: int/float/complex mixing, floor division, modulo, big ints.
print(7 // 2, -7 // 2, 7 // -2, -7 // -2, 7 % 3, -7 % 3, 7 % -3, -7 % -3)
print(7.5 // 2, -7.5 // 2, 7.5 % 2, -7.5 % 2, 7.5 % -2, -0.0 % 1, 0.0 % -1)
print(divmod(7, 3), divmod(-7, 3), divmod(7, -3), divmod(-7, -3), divmod(7.5, -2), divmod(-1e-300, 1))
print(1 / 2, -1 / 2, 6 / 3, type(6 / 3).__name__, 2 ** -2, (-2) ** -1, 0 ** 0, 0.0 ** 0)
print(1 + 2.0, 3 * 1.5, 2 + 1j, (1 + 2j) * (3 - 1j), (1 + 2j) / (1 - 1j), 1j ** 2, abs(3 + 4j))
print(True + 1, True / 2, False * 2.5, True + 1j, 1 == 1.0 == (1 + 0j), hash(1) == hash(1.0) == hash(1 + 0j))
print(complex(1, 2) + 1, (2j).real, (2j).imag, (1 + 2j).conjugate(), 1j.imag)
print(10 ** 20, 2 ** 100, -(2 ** 64), 2 ** 64 // 3, 2 ** 64 % 1000007, (2 ** 64) * (2 ** 64))
big = 123456789012345678901234567890
print(big // 7, big % 7, -big // 7, -big % 7, divmod(big, -97), big >> 40, big << 3, -big >> 5)
print(big & 0xFFFF, big | 1, big ^ big, ~big, big.bit_length(), (-big).bit_length(), int(str(big)) == big)
print(float(big), big / 3, big * 1.0, big == float(big), 2 ** 53 + 1 == float(2 ** 53 + 1))
print(pow(2, 10, 1000), pow(3, -1, 7), pow(-2, 3), pow(2, 0.5), pow(7, 2, -5), pow(10, 18, 2 ** 61 - 1))
print(round(2.5), round(3.5), round(-2.5), round(2.675, 2), round(1234, -2), round(-0.5), round(7, 0))
print(int(-3.9), int(3.9), int("-12"), int(" 0x1f ", 16), int("0b101", 0), int("z", 36), int(True))
print(float("inf") > 10 ** 300, -float("inf"), float("inf") - float("inf") != 0, 1e308 * 10)
print(0.1 + 0.2, 0.1 + 0.2 == 0.3, 1e16 + 1, 1 / 3, 2 / 3, 1e-7, 1.5e300 * 1e10 == float("inf"))
print(abs(-5), abs(-5.5), abs(-0.0), -0.0, 0.0 == -0.0, 5 % 1.5, -5 % 1.5, 2 ** 0.5 * 2 ** 0.5)
print(3 * "ab", [0] * 3, (1,) * 0, "x" * -1, 2 * [1, 2], -1 * [1])
print(7 .bit_length(), (255).to_bytes(2, "big"), int.from_bytes(b"\x01\x00", "little"), (10).__floordiv__(3))
print(1 << 100 >> 99, (1 << 64) - 1, -1 >> 100, -1 << 3, 5 >> 1, -5 >> 1, -5 // 2)
print(divmod(0, 5), divmod(-0.0, 1), 0 // -3, -0 % 5, 0.0 // -1)
print(sum([0.1] * 10), sum([1, 2.5, 3j]), max(1, 2.0), min(-0.0, 0.0), max(0.0, -0.0))
for a, b in [(1, 0), (1.0, 0), (1, 0.0), (5, 0j), (0, 0)]:
    for op in ["/", "//", "%"]:
        try:
            if op == "/":
                a / b
            elif op == "//":
                a // b
            else:
                a % b
        except ZeroDivisionError as e:
            print(type(a).__name__, op, type(b).__name__, "ZeroDivisionError:", e)
        except TypeError as e:
            print(type(a).__name__, op, type(b).__name__, "TypeError:", e)
try:
    divmod(1, 0)
except ZeroDivisionError as e:
    print("ZeroDivisionError:", e)
try:
    0 ** -1
except ZeroDivisionError as e:
    print("ZeroDivisionError:", e)
try:
    0.0 ** -1
except ZeroDivisionError as e:
    print("ZeroDivisionError:", e)
try:
    pow(2, -1, 4)
except ValueError as e:
    print("ValueError:", e)
try:
    1 << -1
except ValueError as e:
    print("ValueError:", e)
try:
    10.0 ** 400
except OverflowError as e:
    print("OverflowError:", e)
try:
    float(10 ** 400)
except OverflowError as e:
    print("OverflowError:", e)
try:
    (1 + 2j) // 2
except TypeError as e:
    print("TypeError:", e)
try:
    (1 + 2j) < 2
except TypeError as e:
    print("TypeError:", e)
try:
    "a" + 1
except TypeError as e:
    print("TypeError:", e)
try:
    1 + "a"
except TypeError as e:
    print("TypeError:", e)
try:
    [1] * 1.5
except TypeError as e:
    print("TypeError:", e)
try:
    -"x"
except TypeError as e:
    print("TypeError:", e)
try:
    ~1.5
except TypeError as e:
    print("TypeError:", e)
try:
    None + None
except TypeError as e:
    print("TypeError:", e)
try:
    "%d" % "x"
except TypeError as e:
    print("TypeError:", e)
try:
    int("12a")
except ValueError as e:
    print("ValueError:", e)
try:
    2 ** 3 ** 0.5j
    print("complex pow ok")
except TypeError as e:
    print("TypeError:", e)
print((-8) ** (1 / 3))
print((-1) ** 0.5)
print(complex("1+2j"), complex(" 3j "), 1e3j, 3j.__class__.__name__, -1j, (-1j).real)
print("%5.2f|%-4d|%x|%o|%e|%g|%%" % (3.14159, 42, 255, 8, 12345.678, 0.00001234))
print(f"{10 / 4:.3f} {2 ** 0.5:10.4f} {-7 // 2:+d} {255:x} {1e20:g} {big:,}")
print(1_000_000 + 0x_ff + 0o_17 + 0b_11, 1_0.5_0, 1e1_0)
print(int.__add__(1, 2), float.__mul__(2.0, 3), (3).__rsub__(10), (2.0).__rtruediv__(1))
print(float.__floordiv__(7.0, 2), int.__mod__(-7, 3), (5).__neg__(), (5).__invert__())
