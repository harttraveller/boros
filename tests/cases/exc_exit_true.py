# sys.exit(True): bool is an int subclass, so status 1 and nothing printed.
import sys
print('exit True')
sys.exit(True)
