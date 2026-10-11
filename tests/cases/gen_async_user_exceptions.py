"""User-defined exception classes crossing asyncio (host) code: results of
gather(return_exceptions=True), Task.exception(), Future.set_exception(),
cancellation messages and async with over asyncio's own managers."""
import asyncio


class ServiceError(Exception):
    def __init__(self, service, code):
        super().__init__('%s failed with %d' % (service, code))
        self.service = service
        self.code = code

    def describe(self):
        return '<%s:%d>' % (self.service, self.code)


async def call_service(name, code):
    await asyncio.sleep(0)
    if code:
        raise ServiceError(name, code)
    return name + ' ok'


def show(label, r):
    if isinstance(r, BaseException):
        print(label, type(r).__name__, isinstance(r, ServiceError), str(r),
              getattr(r, 'code', None))
    else:
        print(label, r)


async def main_gather():
    results = await asyncio.gather(call_service('a', 0), call_service('b', 500),
                                   return_exceptions=True)
    for i, r in enumerate(results):
        show('gather[%d]:' % i, r)
    err = results[1]
    print('describe:', err.describe() if isinstance(err, ServiceError) else 'not a ServiceError')


asyncio.run(main_gather())

async def main_task_exception():
    t = asyncio.create_task(call_service('c', 404))
    try:
        await t
    except ServiceError as e:
        print('await task raised', type(e).__name__, e.code)
    show('task.exception():', t.exception())


asyncio.run(main_task_exception())

async def main_future():
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    try:
        fut.set_exception(ServiceError('d', 503))
    except TypeError as e:
        print('set_exception TypeError', e)
        return
    try:
        await fut
    except ServiceError as e:
        print('future raised', type(e).__name__, e.code)


asyncio.run(main_future())

# asyncio.timeout / Lock are host async context managers: a user exception
# raised in the body must pass through them unchanged
async def main_async_with():
    lock = asyncio.Lock()
    try:
        async with lock:
            raise ServiceError('e', 1)
    except ServiceError as e:
        print('through Lock:', type(e).__name__, e.code, lock.locked())
    try:
        async with asyncio.timeout(10):
            await asyncio.sleep(0)
            raise ServiceError('f', 2)
    except ServiceError as e:
        print('through timeout:', type(e).__name__, e.code)


asyncio.run(main_async_with())

# wait_for with a coroutine that raises a user exception
async def main_wait_for():
    try:
        await asyncio.wait_for(call_service('g', 7), timeout=10)
    except ServiceError as e:
        print('wait_for raised', type(e).__name__, e.code)


asyncio.run(main_wait_for())
