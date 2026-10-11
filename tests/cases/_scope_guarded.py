ran_as = __name__


def main():
    return 'helper main'


if __name__ == '__main__':
    print('helper guard ran (wrong)')
else:
    print('helper imported as', __name__)
