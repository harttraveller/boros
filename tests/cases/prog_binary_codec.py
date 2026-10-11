"""A tiny binary container format: records packed with struct, varint and
zigzag encoding with bit operations, a CRC32 checksum, bytes/bytearray/
memoryview slicing, io.BytesIO streaming, base64/hex dumps, and error
handling for truncated or corrupted input."""
import base64
import io
import struct
import zlib

MAGIC = b"BRS1"
HEADER = struct.Struct("<4sHI")       # magic, record count, crc32 of the body
TYPES = {int: 1, str: 2, bytes: 3, float: 4, list: 5, type(None): 6, bool: 7}


class CodecError(ValueError):
    pass


def zigzag(n):
    return (n << 1) ^ (n >> 63) if n < 0 else n << 1


def unzigzag(z):
    return (z >> 1) ^ -(z & 1)


def write_varint(buf, n):
    if n < 0:
        raise CodecError("varint must be non-negative")
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            buf.append(byte | 0x80)
        else:
            buf.append(byte)
            return


def read_varint(view, pos):
    shift = result = 0
    while True:
        if pos >= len(view):
            raise CodecError("truncated varint at %d" % pos)
        b = view[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, pos
        shift += 7


def encode_value(buf, v):
    t = TYPES.get(type(v))
    if t is None:
        raise CodecError("cannot encode %s" % type(v).__name__)
    buf.append(t)
    if t == 7:
        buf.append(int(v))
    elif t == 1:
        write_varint(buf, zigzag(v))
    elif t in (2, 3):
        data = v.encode("utf-8") if t == 2 else v
        write_varint(buf, len(data))
        buf.extend(data)
    elif t == 4:
        buf.extend(struct.pack("<d", v))
    elif t == 5:
        write_varint(buf, len(v))
        for x in v:
            encode_value(buf, x)


def decode_value(view, pos):
    if pos >= len(view):
        raise CodecError("truncated value at %d" % pos)
    t = view[pos]
    pos += 1
    if t == 7:
        return bool(view[pos]), pos + 1
    if t == 1:
        z, pos = read_varint(view, pos)
        return unzigzag(z), pos
    if t in (2, 3):
        n, pos = read_varint(view, pos)
        if pos + n > len(view):
            raise CodecError("truncated payload: need %d bytes at %d" % (n, pos))
        chunk = bytes(view[pos:pos + n])
        return (chunk.decode("utf-8") if t == 2 else chunk), pos + n
    if t == 4:
        (f,) = struct.unpack_from("<d", view, pos)
        return f, pos + 8
    if t == 5:
        n, pos = read_varint(view, pos)
        items = []
        for _ in range(n):
            x, pos = decode_value(view, pos)
            items.append(x)
        return items, pos
    if t == 6:
        return None, pos
    raise CodecError("unknown type tag %d at %d" % (t, pos - 1))


def dumps(records):
    body = bytearray()
    for r in records:
        encode_value(body, r)
    return HEADER.pack(MAGIC, len(records), zlib.crc32(body)) + bytes(body)


def loads(data):
    if len(data) < HEADER.size:
        raise CodecError("short header")
    magic, count, crc = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise CodecError("bad magic %r" % magic)
    view = memoryview(data)[HEADER.size:]
    if zlib.crc32(view) != crc:
        raise CodecError("checksum mismatch")
    out, pos = [], 0
    for _ in range(count):
        v, pos = decode_value(view, pos)
        out.append(v)
    if pos != len(view):
        raise CodecError("%d trailing bytes" % (len(view) - pos))
    return out


RECORDS = [0, 1, -1, 300, -2 ** 40, "héllo", b"\x00\xffraw", 3.5, [1, ["nested", None], True], False, None, ""]
blob = dumps(RECORDS)
print(len(blob), blob[:10].hex(" "), base64.b64encode(blob[-12:]).decode())
print(loads(blob) == RECORDS, loads(blob))
print([zigzag(n) for n in (0, -1, 1, -2, 2, -64)], [unzigzag(zigzag(n)) for n in (5, -5, 2 ** 62, -(2 ** 62))])
buf = bytearray()
for n in (0, 127, 128, 300, 2 ** 32):
    write_varint(buf, n)
print(buf.hex(), read_varint(buf, 0), read_varint(buf, 1), read_varint(memoryview(buf), 2))

stream = io.BytesIO()
for chunk in (dumps([i, "rec%d" % i]) for i in range(3)):
    stream.write(struct.pack(">H", len(chunk)))
    stream.write(chunk)
stream.seek(0)
frames = []
while True:
    head = stream.read(2)
    if not head:
        break
    (n,) = struct.unpack(">H", head)
    frames.append(loads(stream.read(n)))
print(frames, stream.tell(), len(stream.getvalue()))

corrupt = bytearray(blob)
corrupt[-1] ^= 0xFF
cases = {
    "short": blob[:5], "magic": b"XXXX" + blob[4:], "crc": bytes(corrupt),
    "trailing": blob[:6] + struct.pack("<I", zlib.crc32(blob[10:] + b"\x06")) + blob[10:] + b"\x06",
    "truncated": HEADER.pack(MAGIC, 1, zlib.crc32(b"\x02\x05ab")) + b"\x02\x05ab",
    "tag": HEADER.pack(MAGIC, 1, zlib.crc32(b"\x09")) + b"\x09",
}
for name, data in cases.items():
    try:
        loads(data)
        print(name, "ok?!")
    except CodecError as e:
        print("%-9s CodecError: %s" % (name, e))
for bad in ({1: 2}, -1):
    try:
        if isinstance(bad, int):
            write_varint(bytearray(), bad)
        else:
            dumps([bad])
    except CodecError as e:
        print("CodecError:", e)
mv = memoryview(bytearray(b"abcdef"))
mv[1:3] = b"XY"
print(mv.tobytes(), mv[::2].tobytes(), bytes(mv[-2:]), mv.nbytes, int.from_bytes(b"\x01\x02", "big"),
      (513).to_bytes(2, "little"), struct.calcsize("<4sHI"), bin(0b1011 & ~0b10), (-17) >> 2, 1 << 70)
