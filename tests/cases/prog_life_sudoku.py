"""Conway's game of life on a torus (set of live cells) and a constraint
propagating backtracking sudoku solver."""
from itertools import product, chain
from collections import Counter


class Life:
    def __init__(self, w, h, cells):
        self.w, self.h = w, h
        self.live = frozenset(cells)
        self.generation = 0

    @classmethod
    def parse(cls, text):
        rows = text.strip("\n").split("\n")
        cells = {(x, y) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch == "#"}
        return cls(max(map(len, rows)), len(rows), cells)

    def neighbours(self, x, y):
        for dx, dy in product((-1, 0, 1), repeat=2):
            if dx or dy:
                yield (x + dx) % self.w, (y + dy) % self.h

    def step(self):
        counts = Counter(chain.from_iterable(self.neighbours(*c) for c in self.live))
        self.live = frozenset(c for c, n in counts.items() if n == 3 or (n == 2 and c in self.live))
        self.generation += 1
        return self

    def __str__(self):
        return "\n".join("".join("#" if (x, y) in self.live else "." for x in range(self.w))
                         for y in range(self.h))

    def __len__(self):
        return len(self.live)

    def bbox(self):
        xs = [x for x, _ in self.live]
        ys = [y for _, y in self.live]
        return (min(xs), min(ys), max(xs), max(ys)) if self.live else None


glider = Life.parse("""
.#......
..#.....
###.....
........
........
........
""")
print(glider, len(glider), sep="\n")
seen = {}
for i in range(24):
    key = glider.live
    if key in seen:
        print("cycle: generation", glider.generation, "repeats", seen[key])
        break
    seen[key] = glider.generation
    glider.step()
print(glider.generation, glider.bbox())
print(glider)

blinker = Life.parse(".....\n..#..\n..#..\n..#..\n.....")
states = [str(blinker.step()) for _ in range(3)]
print(states[0] == states[2], states[0] != states[1], states[0].replace("\n", "/"))

# ---------------------------------------------------------------- sudoku
DIGITS = "123456789"
ROWS = "ABCDEFGHI"
SQUARES = [r + c for r in ROWS for c in DIGITS]
UNITLIST = ([[r + c for c in DIGITS] for r in ROWS] +
            [[r + c for r in ROWS] for c in DIGITS] +
            [[r + c for r in rs for c in cs] for rs in ("ABC", "DEF", "GHI") for cs in ("123", "456", "789")])
UNITS = {s: [u for u in UNITLIST if s in u] for s in SQUARES}
PEERS = {s: set(sum(UNITS[s], [])) - {s} for s in SQUARES}


class Contradiction(Exception):
    pass


stats = {"assign": 0, "search": 0}


def assign(values, s, d):
    stats["assign"] += 1
    for other in values[s].replace(d, ""):
        eliminate(values, s, other)
    return values


def eliminate(values, s, d):
    if d not in values[s]:
        return
    values[s] = values[s].replace(d, "")
    if not values[s]:
        raise Contradiction("no values left for " + s)
    if len(values[s]) == 1:
        d2 = values[s]
        for s2 in PEERS[s]:
            eliminate(values, s2, d2)
    for u in UNITS[s]:
        places = [sq for sq in u if d in values[sq]]
        if not places:
            raise Contradiction("no place for %s in unit of %s" % (d, s))
        if len(places) == 1:
            assign(values, places[0], d)


def parse_grid(grid):
    chars = [c for c in grid if c in DIGITS or c in "0."]
    if len(chars) != 81:
        raise ValueError("grid must have 81 cells, got %d" % len(chars))
    values = {s: DIGITS for s in SQUARES}
    for s, d in zip(SQUARES, chars):
        if d in DIGITS:
            assign(values, s, d)
    return values


def search(values):
    stats["search"] += 1
    if all(len(values[s]) == 1 for s in SQUARES):
        return values
    n, s = min((len(values[s]), s) for s in SQUARES if len(values[s]) > 1)
    for d in values[s]:
        try:
            return search(assign(values.copy(), s, d))
        except Contradiction:
            continue
    raise Contradiction("dead end at " + s)


def show(values):
    lines = []
    for i, r in enumerate(ROWS):
        if i in (3, 6):
            lines.append("------+-------+------")
        row = ""
        for j, c in enumerate(DIGITS):
            row += values[r + c] + (" | " if j in (2, 5) else " ")
        lines.append(row.rstrip())
    return "\n".join(lines)


EASY = "003020600900305001001806400008102900700000008006708200002609500800203009005010300"
HARD = "4.....8.5.3..........7......2.....6.....8.4......1.......6.3.7.5..2.....1.4......"
for name, puzzle in (("easy", EASY), ("hard", HARD)):
    stats.update(assign=0, search=0)
    sol = search(parse_grid(puzzle))
    print(name, stats)
    print(show(sol))
    ok = all(sorted(sol[s] for s in u) == list(DIGITS) for u in UNITLIST)
    print("valid:", ok)

for bad in ("123", "11" + "." * 79):
    try:
        search(parse_grid(bad))
    except (ValueError, Contradiction) as e:
        print(type(e).__name__ + ":", e)
