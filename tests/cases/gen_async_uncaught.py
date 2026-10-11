"""A program that ends with an uncaught exception raised inside an
interpreted coroutine awaited through several layers under asyncio.run."""
import asyncio


class InsufficientFunds(Exception):
    def __init__(self, needed):
        super().__init__('need %d more' % needed)
        self.needed = needed


async def withdraw(balance, amount):
    await asyncio.sleep(0)
    if amount > balance:
        raise InsufficientFunds(amount - balance)
    return balance - amount


async def process(ops):
    balance = 100
    for op in ops:
        balance = await withdraw(balance, op)
        print('balance', balance)
    return balance


async def main():
    results = await asyncio.gather(process([10, 20]), process([50]))
    print('results', results)
    await process([30, 80])


asyncio.run(main())
