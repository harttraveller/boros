"""Bank and inventory simulation: inheritance, properties with validation,
class/static methods, custom exception hierarchy, __slots__, rich
comparisons, context managers for transactions, Decimal money."""
from decimal import Decimal


class BankError(Exception):
    pass


class InsufficientFunds(BankError):
    def __init__(self, account, amount):
        super().__init__("account %s: cannot withdraw %s, balance is %s" % (account.number, amount, account.balance))
        self.account = account
        self.amount = amount


class AccountFrozen(BankError):
    pass


class Account:
    _next_number = 1000
    interest_rate = Decimal("0.00")
    kind = "basic"

    def __init__(self, owner, balance=Decimal("0")):
        self.owner = owner
        self._balance = Decimal(balance)
        self.number = Account._allocate()
        self.frozen = False
        self.history = []

    @classmethod
    def _allocate(cls):
        n = cls._next_number
        Account._next_number += 1
        return n

    @staticmethod
    def money(x):
        return Decimal(x).quantize(Decimal("0.01"))

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        if value < 0 and not self.allows_overdraft():
            raise InsufficientFunds(self, -value)
        self._balance = self.money(value)

    def allows_overdraft(self):
        return False

    def deposit(self, amount):
        self._check()
        if amount <= 0:
            raise ValueError("deposit must be positive")
        self.balance += amount
        self.history.append(("dep", amount))
        return self

    def withdraw(self, amount):
        self._check()
        if self.balance - amount < self.floor():
            raise InsufficientFunds(self, amount)
        self.balance -= amount
        self.history.append(("wd", amount))
        return self

    def floor(self):
        return 0

    def _check(self):
        if self.frozen:
            raise AccountFrozen("account %d is frozen" % self.number)

    def month_end(self):
        interest = self.money(self.balance * self.interest_rate)
        if interest:
            self.balance += interest
            self.history.append(("int", interest))

    def __eq__(self, other):
        if not isinstance(other, Account):
            return NotImplemented
        return self.balance == other.balance

    def __lt__(self, other):
        if not isinstance(other, Account):
            return NotImplemented
        return self.balance < other.balance

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        r = self.__le__(other)
        return r if r is NotImplemented else not r

    __hash__ = object.__hash__

    def __repr__(self):
        return "%s(%r, %s)" % (type(self).__name__, self.owner, self.balance)


class Savings(Account):
    interest_rate = Decimal("0.02")
    kind = "savings"

    def withdraw(self, amount):
        if len([h for h in self.history if h[0] == "wd"]) >= 2:
            raise BankError("savings: withdrawal limit reached")
        return super().withdraw(amount)


class Checking(Account):
    kind = "checking"

    def __init__(self, owner, balance=0, overdraft=100):
        super().__init__(owner, balance)
        self.overdraft = overdraft

    def allows_overdraft(self):
        return True

    def floor(self):
        return -self.overdraft


class Bank:
    def __init__(self, name):
        self.name = name
        self.accounts = {}

    def open(self, cls, owner, *args, **kw):
        acct = cls(owner, *args, **kw)
        self.accounts[acct.number] = acct
        return acct

    def transfer(self, src, dst, amount):
        with Transaction(self, src, dst):
            src.withdraw(amount)
            dst.deposit(amount)

    def total(self):
        return sum((a.balance for a in self.accounts.values()), Decimal(0))

    def __iter__(self):
        return iter(sorted(self.accounts.values(), key=lambda a: a.number))

    def __len__(self):
        return len(self.accounts)

    def __contains__(self, number):
        return number in self.accounts


class Transaction:
    log = []

    def __init__(self, bank, *accounts):
        self.bank = bank
        self.accounts = accounts

    def __enter__(self):
        self.saved = [(a, a.balance, len(a.history)) for a in self.accounts]
        return self

    def __exit__(self, et, ev, tb):
        if et is None:
            Transaction.log.append("commit")
            return False
        for acct, bal, n in self.saved:
            acct._balance = bal
            del acct.history[n:]
        Transaction.log.append("rollback:" + et.__name__)
        return issubclass(et, InsufficientFunds)


class Item:
    def __init__(self, sku, price, qty=0, tags=None):
        self.sku = sku
        self.price = price
        self.qty = qty
        self.tags = tags if tags is not None else []

    @property
    def value(self):
        return self.price * self.qty

    def __repr__(self):
        return "Item(sku=%r, price=%r, qty=%r)" % (self.sku, self.price, self.qty)

    def __eq__(self, other):
        return isinstance(other, Item) and self.sku == other.sku

    def __lt__(self, other):
        return self.sku < other.sku


class Inventory:
    __slots__ = ("items", "events")

    def __init__(self):
        self.items = {}
        self.events = []

    def add(self, item):
        if item.sku in self.items:
            self.items[item.sku].qty += item.qty
        else:
            self.items[item.sku] = item
        self.events.append("add %s x%d" % (item.sku, item.qty))

    def remove(self, sku, qty):
        it = self.items.get(sku)
        if it is None:
            raise KeyError(sku)
        if it.qty < qty:
            raise ValueError("only %d of %s left" % (it.qty, sku))
        it.qty -= qty
        if not it.qty:
            del self.items[sku]

    def __getitem__(self, sku):
        return self.items[sku]


bank = Bank("First Boros")
alice = bank.open(Savings, "alice", "500.00")
bob = bank.open(Checking, "bob", 50, overdraft=200)
carol = bank.open(Account, "carol")
print(alice, bob, carol, len(bank), alice.number in bank, 1 in bank)

bank.transfer(alice, bob, Decimal("120.50"))
bank.transfer(bob, carol, 300)            # bob goes into overdraft
bank.transfer(carol, alice, 1000)         # insufficient: rolled back, suppressed
try:
    bank.transfer(alice, carol, -5)       # ValueError from deposit, rolled back, propagates
except ValueError as e:
    print("ValueError:", e)
alice.withdraw(10)
try:
    alice.withdraw(1)
except BankError as e:
    print(type(e).__name__, e)
carol.frozen = True
try:
    carol.deposit(1)
except AccountFrozen as e:
    print("frozen:", e, isinstance(e, BankError))
try:
    carol.balance = -1
except InsufficientFunds as e:
    print("setter:", e, e.amount)
carol.frozen = False

for acct in bank:
    acct.month_end()
    print("%-8s %-8s %10s %s" % (acct.owner, acct.kind, acct.balance, acct.history))
print("total", bank.total(), Transaction.log)
print(sorted(bank), max(bank).owner, alice > bob, alice == alice, alice != bob, bob <= carol, carol >= bob)
print(Account.money("2.345"), Savings.interest_rate, Checking.kind, Checking.__mro__[1].__name__)

inv = Inventory()
inv.add(Item("B-2", Decimal("2.50"), 4, ["blue"]))
inv.add(Item("A-1", Decimal("10"), 1))
inv.add(Item("B-2", Decimal("2.50"), 6))
inv.remove("A-1", 1)
for bad in (("A-1", 1), ("B-2", 11)):
    try:
        inv.remove(*bad)
    except (KeyError, ValueError) as e:
        print(type(e).__name__, e)
print(inv.items, inv["B-2"].value, inv["B-2"].tags, inv.events)
print(sorted([Item("z", 1), Item("a", 2), Item("m", 3)]), Item("q", 1) == Item("q", 99), Item("q", 1) != Item("r", 1))
try:
    hash(Item("q", 1))
except TypeError as e:
    print("TypeError:", e)
try:
    inv.extra = 1
except AttributeError as e:
    print("slots:", e)
