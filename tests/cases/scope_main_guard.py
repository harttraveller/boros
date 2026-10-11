import sys
import _scope_guarded


def main(argv):
    print('main called with', len(argv), 'arg(s)')
    print(_scope_guarded.ran_as, _scope_guarded.main())
    return 3


if __name__ == '__main__':
    print('guard ran in', __name__)
    code = main(sys.argv)
    print(type(sys.argv).__name__, sys.argv[0].endswith('scope_main_guard.py'))
    sys.exit(code)
print('not reached')
