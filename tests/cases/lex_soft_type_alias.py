# The `type` soft keyword: `type X = ...` creates a lazily evaluated
# typing.TypeAliasType, while `type` stays usable as a name elsewhere.

type IntList = list[int]
print(IntList, type(IntList).__name__, IntList.__name__)
print(IntList.__value__)
type Lazy = UndefinedName      # not evaluated until __value__ is read
print(Lazy.__name__)
try:
    Lazy.__value__
except NameError as e:
    print('NameError on __value__:', e)
type Pair[T] = tuple[T, T]
print(Pair.__name__, Pair.__type_params__)
print(type(5).__name__, type('s') is str)
type = 'now a string'
print(type)
