# Uncaught subclass of SystemExit defined in the program, with an int code.
class Stop(SystemExit):
    def __init__(self, code):
        super().__init__(code)
        self.extra = 'x'


def run():
    raise Stop(4)


print('before')
run()
