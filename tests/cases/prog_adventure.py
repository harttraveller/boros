"""Text adventure: a state machine driven by a dict of command handlers,
closures over game state, a scripted input stream, match statements for
command parsing, and an uncaught custom exception at the very end."""


class GameOver(Exception):
    def __init__(self, reason, score):
        super().__init__(reason)
        self.score = score


class Room:
    def __init__(self, name, desc, exits=None, items=()):
        self.name = name
        self.desc = desc
        self.exits = dict(exits or {})
        self.items = list(items)
        self.locked = {}

    def __repr__(self):
        return "Room(%s)" % self.name


def build_world():
    rooms = {
        "hall": Room("hall", "A dusty hall.", {"north": "library", "east": "kitchen"}, ["lamp"]),
        "library": Room("library", "Shelves of books.", {"south": "hall", "up": "attic"}, ["book"]),
        "kitchen": Room("kitchen", "Smells of old bread.", {"west": "hall", "down": "cellar"}, ["knife", "bread"]),
        "cellar": Room("cellar", "Pitch black and damp.", {"up": "kitchen"}, ["key"]),
        "attic": Room("attic", "A locked chest sits here.", {"down": "library"}, ["chest"]),
    }
    rooms["library"].locked["up"] = "key"
    return rooms


def make_game(script):
    rooms = build_world()
    state = {"room": "hall", "inventory": [], "moves": 0, "score": 0, "lit": False}
    out = []
    handlers = {}

    def say(*parts):
        out.append(" ".join(str(p) for p in parts))

    def command(*names):
        def register(fn):
            for n in names:
                handlers[n] = fn
            fn.names = names
            return fn
        return register

    def here():
        return rooms[state["room"]]

    @command("look", "l")
    def look(args):
        r = here()
        if r.name == "cellar" and not state["lit"]:
            say("It is too dark to see.")
            return
        say("[%s] %s" % (r.name, r.desc))
        if r.items:
            say("You see:", ", ".join(sorted(r.items)))
        say("Exits:", " ".join(sorted(r.exits)))

    @command("go", "walk")
    def go(args):
        if not args:
            say("Go where?")
            return
        direction = args[0]
        r = here()
        if direction not in r.exits:
            say("You can't go %s." % direction)
            return
        need = r.locked.get(direction)
        if need and need not in state["inventory"]:
            say("The way %s is locked." % direction)
            return
        state["room"] = r.exits[direction]
        state["moves"] += 1
        look([])

    @command("take", "get")
    def take(args):
        r = here()
        for item in args:
            if item == "chest":
                say("The chest is far too heavy.")
            elif item in r.items:
                r.items.remove(item)
                state["inventory"].append(item)
                state["score"] += 5
                say("Taken:", item)
            else:
                say("No %s here." % item)

    @command("drop")
    def drop(args):
        for item in args:
            try:
                state["inventory"].remove(item)
            except ValueError:
                say("You don't have", item)
            else:
                here().items.append(item)
                say("Dropped", item)

    @command("use")
    def use(args):
        match args:
            case ["lamp"] if "lamp" in state["inventory"]:
                state["lit"] = not state["lit"]
                say("The lamp is now", "on" if state["lit"] else "off")
            case ["key", "chest"] | ["key", "on", "chest"]:
                if state["room"] != "attic":
                    say("There is no chest here.")
                elif "key" not in state["inventory"]:
                    say("You have no key.")
                else:
                    state["score"] += 50
                    raise GameOver("You open the chest and find the treasure!", state["score"])
            case [thing, *rest]:
                say("You can't use %s%s." % (thing, " like that" if rest else ""))
            case []:
                say("Use what?")

    @command("inventory", "i")
    def inventory(args):
        say("You carry:", ", ".join(state["inventory"]) or "nothing")

    @command("help")
    def help_(args):
        groups = {}
        for name, fn in handlers.items():
            groups.setdefault(fn.__name__, []).append(name)
        say("Commands:", "; ".join("/".join(v) for k, v in sorted(groups.items())))

    def step(line):
        words = line.lower().split()
        match words:
            case []:
                return
            case ["n" | "north" | "s" | "south" | "e" | "east" | "w" | "west" | "up" | "down" as d]:
                full = {"n": "north", "s": "south", "e": "east", "w": "west"}.get(d, d)
                handlers["go"]([full])
            case [verb, *args] if verb in handlers:
                handlers[verb](args)
            case [verb, *_]:
                say("I don't know how to %r." % verb)

    def run():
        for line in script:
            out.append("> " + line)
            try:
                step(line)
            except GameOver as e:
                say(e)
                say("Final score:", e.score, "in", state["moves"], "moves")
                return True
        return False

    return run, out, state


SCRIPT = """look
take lamp
go north
up
s
e
take knife bread spoon
down
look
use lamp
look
take key
inventory
drop spoon
drop bread
use knife quickly
use
dance wildly
up
w
n
up
take chest
use key on chest
look""".split("\n")

run, out, state = make_game(SCRIPT)
won = run()
print("\n".join(out))
print("won:", won, "inventory:", state["inventory"])

# second play-through: the help text, then an unhandled game over escapes
run2, out2, state2 = make_game(["help", "go nowhere", "e", "down", "use lamp"])
run2()
print("\n".join(out2))
state2["score"] = 7
raise GameOver("eaten by a grue", state2["score"])
