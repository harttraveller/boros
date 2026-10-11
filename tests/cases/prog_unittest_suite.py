"""A small shopping-cart library with a unittest test suite, run through
unittest's own loader and TextTestRunner (into a StringIO) the way a CI
script would, then summarised deterministically: setUp/tearDown,
setUpClass, assertRaises as context manager and callable, subTest,
skip/expectedFailure decorators, and intentionally failing tests."""
import io
import unittest


class OutOfStock(Exception):
    pass


class Cart:
    def __init__(self, stock):
        self.stock = dict(stock)
        self.items = {}

    def add(self, sku, qty=1):
        if qty <= 0:
            raise ValueError("qty must be positive")
        if self.stock.get(sku, 0) < qty:
            raise OutOfStock(sku)
        self.stock[sku] -= qty
        self.items[sku] = self.items.get(sku, 0) + qty

    def total(self, prices):
        return round(sum(prices[s] * q for s, q in self.items.items()), 2)

    def __len__(self):
        return sum(self.items.values())


PRICES = {"apple": 0.5, "pear": 0.75, "fig": 2.1}
EVENTS = []


class CartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        EVENTS.append("setUpClass")
        cls.shared_stock = {"apple": 10, "pear": 2, "fig": 1}

    def setUp(self):
        self.cart = Cart(self.shared_stock)

    def tearDown(self):
        EVENTS.append("tearDown:" + self._testMethodName)

    def test_add_and_len(self):
        self.cart.add("apple", 3)
        self.cart.add("pear")
        self.assertEqual(len(self.cart), 4)
        self.assertIn("pear", self.cart.items)
        self.assertEqual(self.cart.stock["apple"], 7)

    def test_total(self):
        self.cart.add("apple", 2)
        self.cart.add("fig")
        self.assertAlmostEqual(self.cart.total(PRICES), 3.1)

    def test_out_of_stock(self):
        with self.assertRaises(OutOfStock) as cm:
            self.cart.add("fig", 2)
        self.assertEqual(str(cm.exception), "fig")
        self.assertRaises(ValueError, self.cart.add, "apple", 0)

    def test_quantities(self):
        for qty, ok in [(1, True), (2, True), (3, False)]:
            with self.subTest(qty=qty):
                cart = Cart(self.shared_stock)
                if ok:
                    cart.add("pear", qty)
                else:
                    self.assertRaises(OutOfStock, cart.add, "pear", qty)

    def test_wrong_total(self):
        self.cart.add("pear", 2)
        self.assertEqual(self.cart.total(PRICES), 1.4, "pear pricing")

    def test_broken(self):
        self.cart.add("kiwi")

    @unittest.skip("not implemented yet")
    def test_discounts(self):
        self.fail("should not run")

    @unittest.expectedFailure
    def test_known_bug(self):
        self.assertTrue(len(Cart({})) == 1)

    def helper_not_a_test(self):
        raise AssertionError("never collected")


class StockTests(unittest.TestCase):
    def test_shared_stock_untouched(self):
        self.assertEqual(CartTests.shared_stock, {"apple": 10, "pear": 2, "fig": 1})

    def test_subtest_failure(self):
        for n in range(3):
            with self.subTest(n=n):
                self.assertNotEqual(n, 1)


loader = unittest.TestLoader()
print(loader.getTestCaseNames(CartTests))
suite = unittest.TestSuite()
suite.addTests(loader.loadTestsFromTestCase(CartTests))
suite.addTests(loader.loadTestsFromTestCase(StockTests))
print("collected", suite.countTestCases())
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)


def name(test):
    return test.id().split(".", 1)[1]


def last_line(text):
    return text.strip().splitlines()[-1]


print("ran", result.testsRun, "ok", result.wasSuccessful())
for test, tb in result.failures:
    print("FAIL ", name(test), "|", last_line(tb))
for test, tb in result.errors:
    print("ERROR", name(test), "|", last_line(tb))
for test, reason in result.skipped:
    print("SKIP ", name(test), "|", reason)
print("expected failures:", [name(t) for t, _ in result.expectedFailures])
print(EVENTS[0], len(EVENTS), sorted(e for e in EVENTS if "quant" in e or "broken" in e))
