# Python 3.13 "too many values" messages do not include the actual count.
for thunk in [lambda: [(a, b) for a, b in [(1, 2, 3)]], lambda: [(a, b) for a, b in [[1, 2, 3, 4, 5]]],
              lambda: [(a, b) for a, b in ["xyz"]], lambda: [(a, b) for a, b in [iter(range(9))]],
              lambda: [(a, b) for a, b in [{1: 0, 2: 0, 3: 0}]]]:
    try:
        thunk()
    except ValueError as e:
        print("ValueError:", e)
try:
    a, b = 1, 2, 3
except ValueError as e:
    print("ValueError:", e)
t = (1, 2, 3)
try:
    x, y = t
except ValueError as e:
    print("ValueError:", e)
try:
    for p, q in [[1, 2, 3]]:
        pass
except ValueError as e:
    print("ValueError:", e)
