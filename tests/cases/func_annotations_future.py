# With postponed evaluation, annotations are stored as strings and may name
# things that are defined later.
from __future__ import annotations


def f(a: Later, b: list[Later] = None, *args: int, k: dict[str, int] | None = None) -> Later:
    return a


class Later:
    def m(self, other: Later) -> tuple[int, ...]:
        return ()


print(f.__annotations__)
print(Later.m.__annotations__)
print(f(1))
