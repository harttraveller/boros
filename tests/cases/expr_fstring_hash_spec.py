# '#' inside an f-string format spec is the "alternate form" flag, not a comment.
n = 255
print(f"{n:#x}", f"{n:#o}", f"{n:#b}", f"{n:#010x}", f"{3.0:#g}", f"{n:{'#x'}}")
print(f"{'#'}", f"{'a#b'!r}", f"{n!r:>6}")
