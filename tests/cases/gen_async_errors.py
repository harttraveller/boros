"""Error behaviour of await / async for / async with on objects that do not
implement the protocols, with the exact messages CPython produces."""
import asyncio


async def value():
    return 1


def plain_gen():
    yield 1


class NoAiter:
    pass


class NoAwait:
    pass


class AiterOnly:
    def __aiter__(self):
        return self


class BadAnext:
    def __aiter__(self):
        return self

    def __anext__(self):
        return 42


class SyncCM:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class AenterOnly:
    async def __aenter__(self):
        return self


async def check(label, coro_fn):
    try:
        r = await coro_fn()
        print(label, 'no error', r)
    except Exception as e:
        print(label, type(e).__name__, e)


async def await_int():
    return await 5


async def await_generator():
    return await plain_gen()


async def await_instance():
    return await NoAwait()


async def async_for_list():
    lst = [1, 2]
    async for x in lst:
        pass


async def async_for_noaiter():
    async for x in NoAiter():
        pass


async def async_for_no_anext():
    async for x in AiterOnly():
        pass


async def async_for_bad_anext():
    async for x in BadAnext():
        pass


async def async_with_sync_cm():
    async with SyncCM():
        pass


async def async_with_aenter_only():
    async with AenterOnly():
        pass


async def main():
    await check('await int:', await_int)
    await check('await generator:', await_generator)
    await check('await instance:', await_instance)
    await check('async for list:', async_for_list)
    await check('async for no __aiter__:', async_for_noaiter)
    await check('async for no __anext__:', async_for_no_anext)
    await check('async for bad __anext__:', async_for_bad_anext)
    await check('async with sync cm:', async_with_sync_cm)
    await check('async with no __aexit__:', async_with_aenter_only)


asyncio.run(main())
