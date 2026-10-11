# Error messages for non-iterable * in list/tuple displays and non-mapping ** in dict displays.
for thunk in [lambda: [*5], lambda: (*1,), lambda: [0, *None], lambda: (*3.5, 1)]:
    try:
        thunk()
    except TypeError as e:
        print("TypeError:", e)
for thunk in [lambda: {*None}, lambda: {**5}, lambda: {**[1]}, lambda: {"a": 1, **None}]:
    try:
        thunk()
    except TypeError as e:
        print("TypeError:", e)
