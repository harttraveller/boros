# Uncaught exception class defined in __main__ with no message, raised from a method.


class EmptyError(Exception):
    pass


class Service:
    def run(self):
        self.step()

    def step(self):
        raise EmptyError


Service().run()
