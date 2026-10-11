"""Graph algorithms: Dijkstra with heapq, BFS with deque, topological sort,
connected components with union-find, and A* on a small grid."""
import heapq
from collections import defaultdict, deque, namedtuple

Edge = namedtuple("Edge", "src dst weight")


class Graph:
    def __init__(self, directed=False):
        self.adj = defaultdict(list)
        self.directed = directed
        self.nodes = set()

    def add(self, a, b, w=1):
        self.adj[a].append((b, w))
        self.nodes.update((a, b))
        if not self.directed:
            self.adj[b].append((a, w))

    @classmethod
    def from_edges(cls, edges, directed=False):
        g = cls(directed)
        for e in edges:
            g.add(*e)
        return g

    def dijkstra(self, start):
        dist = {start: 0}
        prev = {}
        heap = [(0, start)]
        done = set()
        while heap:
            d, u = heapq.heappop(heap)
            if u in done:
                continue
            done.add(u)
            for v, w in self.adj[u]:
                nd = d + w
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))
        return dist, prev

    def path(self, start, goal):
        dist, prev = self.dijkstra(start)
        if goal not in dist:
            return None, float("inf")
        p = [goal]
        while p[-1] != start:
            p.append(prev[p[-1]])
        return p[::-1], dist[goal]

    def bfs(self, start):
        seen = {start: 0}
        q = deque([start])
        order = []
        while q:
            u = q.popleft()
            order.append(u)
            for v, _ in sorted(self.adj[u]):
                if v not in seen:
                    seen[v] = seen[u] + 1
                    q.append(v)
        return order, seen

    def toposort(self):
        indeg = {n: 0 for n in self.nodes}
        for u in list(self.adj):
            for v, _ in self.adj[u]:
                indeg[v] += 1
        ready = sorted(n for n, d in indeg.items() if d == 0)
        heapq.heapify(ready)
        out = []
        while ready:
            u = heapq.heappop(ready)
            out.append(u)
            for v, _ in self.adj[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    heapq.heappush(ready, v)
        if len(out) != len(self.nodes):
            raise ValueError("graph has a cycle among %s" % sorted(n for n in self.nodes if indeg[n]))
        return out


class DSU:
    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        self.rank.setdefault(x, 0)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True


def kruskal(edges):
    dsu = DSU()
    tree = [e for e in sorted(edges, key=lambda e: (e.weight, e.src, e.dst)) if dsu.union(e.src, e.dst)]
    return tree, sum(e.weight for e in tree)


def astar(grid, start, goal):
    rows, cols = len(grid), len(grid[0])

    def h(p):
        return abs(p[0] - goal[0]) + abs(p[1] - goal[1])

    open_heap = [(h(start), 0, start)]
    came = {start: None}
    g = {start: 0}
    expanded = 0
    while open_heap:
        f, cost, cur = heapq.heappop(open_heap)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = came[cur]
            return path[::-1], expanded
        if cost > g[cur]:
            continue
        expanded += 1
        r, c = cur
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != "#":
                nxt = (nr, nc)
                ng = cost + 1
                if ng < g.get(nxt, 1 << 30):
                    g[nxt] = ng
                    came[nxt] = cur
                    heapq.heappush(open_heap, (ng + h(nxt), ng, nxt))
    return None, expanded


EDGES = [Edge(*t) for t in [("A", "B", 7), ("A", "C", 9), ("A", "F", 14), ("B", "C", 10), ("B", "D", 15),
                            ("C", "D", 11), ("C", "F", 2), ("D", "E", 6), ("E", "F", 9), ("G", "H", 1)]]
g = Graph.from_edges(EDGES)
dist, _ = g.dijkstra("A")
print(sorted(dist.items()))
for goal in "EDFH":
    print(goal, *g.path("A", goal))
print(g.bfs("A"))
print(kruskal(EDGES))
print(Edge("x", "y", 3)._asdict(), Edge._fields, EDGES[0]._replace(weight=0))

dag = Graph.from_edges([("shirt", "tie", 1), ("tie", "jacket", 1), ("pants", "shoes", 1), ("pants", "belt", 1),
                        ("belt", "jacket", 1), ("shirt", "belt", 1), ("socks", "shoes", 1)], directed=True)
print(dag.toposort())
dag.add("jacket", "shirt")
try:
    dag.toposort()
except ValueError as e:
    print("cycle:", e)

GRID = [
    "..........",
    ".######...",
    "......#.#.",
    ".####.#.#.",
    ".#....#.#.",
    ".#.####.#.",
    "...#......",
]
path, expanded = astar(GRID, (0, 0), (6, 9))
print(len(path) - 1, expanded, path[:4], path[-3:])
canvas = [list(row) for row in GRID]
for r, c in path:
    canvas[r][c] = "*"
print("\n".join("".join(row) for row in canvas))
print(astar([".#.", "##.", "..."], (0, 0), (2, 2)))

# word ladder via BFS on implicit graph
WORDS = {"cold", "cord", "card", "ward", "warm", "worm", "word", "wood", "corm", "wore", "core"}


def ladder(a, b):
    q = deque([[a]])
    seen = {a}
    while q:
        p = q.popleft()
        if p[-1] == b:
            return p
        w = p[-1]
        for i in range(len(w)):
            for ch in "abcdefghijklmnopqrstuvwxyz":
                n = w[:i] + ch + w[i + 1:]
                if n in WORDS and n not in seen:
                    seen.add(n)
                    q.append(p + [n])


print(ladder("cold", "warm"))
