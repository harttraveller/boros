import sys
print('stdout line')
print('first stderr line', file=sys.stderr)
print('last', 'stderr', 'line', sep='/', file=sys.stderr, flush=True)
sys.exit(3)
