# Numeric literals: ints in all bases, underscores, floats, exponents,
# imaginary numbers.

def show(*vals):
    print(' '.join('%s:%s' % (type(v).__name__, repr(v)) for v in vals))

show(0, 00, 000, 7, 10, 123456789, 0_0, 1_000_000)
show(0x0, 0xff, 0XFF, 0xDead_Beef, 0x_1f, 0x1_2_3)
show(0o0, 0o17, 0O777, 0o_7, 0o1_7)
show(0b0, 0b1010, 0B11, 0b_1, 0b1111_0000)
show(1.0, 1., .5, 0.0, 00.5, 09.5, 1_0.5, 1.2_5, 0.000_001)
show(1e3, 1E3, 1e+3, 1e-3, 1.5e10, .5e-2, 5.e2, 1_0e1_0, 1e0, 0e0)
show(1e308, 1e-320, 1e400, -1e400, 123456789012345678901234567890.0)
show(1j, 1J, 0j, 2.5j, .5j, 5.j, 1e3j, 1e-3J, 1_0j, 09j, 00j)
show(1 + 2j, 3 - 4j, -1j, (1j) ** 2, 1j * 1j)
show(12345678901234567890123456789, 0xffffffffffffffffffffffffffffffff, -0b1, -0o17)
show(10 ** 20, 2 ** 64, 2 ** -1, 7 // 2, -7 // 2, 7 % -3, 1 / 3)
show(-0.0, +0.0, -0, +5, --5, -+-5, ~0)
show(0.1 + 0.2, 1e16, 1e15, 1.5e-5, 0.0001, 1e-4, 100.0, 1e22, 1e21 * 10)
show(float('inf') == 1e400, 1e400 - 1e400 != 1e400 - 1e400)
show(0xa + 0o10 + 0b10 + 10, 1_2 * 3_4)
# attribute access on literals
show((1).bit_length(), 1 .bit_length(), 1..hex(), 1.0.is_integer(), 0x10 .real, 1j.imag)
show(255 .to_bytes(2, 'big'), (3.5).as_integer_ratio(), 1e3.is_integer())
# literals next to operators/keywords without spaces
x = 1+2-3*4//5%6**2
show(x, 1<2, 3>=3, 0x1f&0b1, 1|2^3, 1<<3>>1)
show([0x1,0o2,0b11,4.,.5,6e0,7j])
show(1 if True else 2, 0 or 1.5, 1 and 0x0)
# the same numbers via eval / int() / float() / complex()
for src in ['0x_ff', '1_000', '0o777', '0b101', '1e1_0', '1_0.0_1', '3.14j', '0_0', '00', '1.e5']:
    print(src, repr(eval(src)))
print(int('1_000'), int('0x1f', 16), int('0b11', 0), float('1_0.5'), complex('1+2j'))
print(repr(0.1), repr(1/3), repr(2.0**0.5), str(1e-7), str(123456789.123456789))
