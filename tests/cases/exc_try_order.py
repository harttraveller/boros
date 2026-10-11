# try/except/else/finally execution order, control flow through finally.
log = []


def t1(fail):
    try:
        log.append('body')
        if fail:
            raise ValueError('x')
        log.append('body-end')
    except ValueError:
        log.append('except')
    else:
        log.append('else')
    finally:
        log.append('finally')
    log.append('after')


t1(False)
print(log)
log.clear()
t1(True)
print(log)
log.clear()


def ret_in_try():
    try:
        return 'try'
    finally:
        log.append('fin')


print(ret_in_try(), log)
log.clear()


def finally_overrides():
    try:
        return 1
    finally:
        return 2


print(finally_overrides())


def finally_swallows():
    try:
        raise KeyError('lost')
    finally:
        return 'swallowed'


print(finally_swallows())


def except_return_then_finally():
    try:
        raise ValueError
    except ValueError:
        log.append('handler')
        return 'from-handler'
    finally:
        log.append('finally')


print(except_return_then_finally(), log)
log.clear()


def else_return():
    try:
        pass
    except Exception:
        return 'no'
    else:
        return 'else'
    finally:
        log.append('f')


print(else_return(), log)
log.clear()


def loop_break_continue():
    out = []
    for i in range(6):
        try:
            if i == 1:
                continue
            if i == 4:
                break
            out.append(i)
        finally:
            out.append('f%d' % i)
    else:
        out.append('else-not-run')
    return out


print(loop_break_continue())


def break_in_finally_swallows():
    out = []
    for i in range(3):
        try:
            out.append(i)
            raise RuntimeError(i)
        finally:
            out.append('fin')
            break
    return out


print(break_in_finally_swallows())


def continue_in_finally():
    out = []
    for i in range(3):
        try:
            if i == 1:
                raise ValueError
            out.append(i)
        finally:
            continue
    return out


print(continue_in_finally())


def while_try():
    n = 0
    out = []
    while True:
        n += 1
        try:
            if n % 2:
                continue
            if n > 6:
                return out
            out.append(n)
        finally:
            out.append(-n)


print(while_try())


def nested():
    out = []
    try:
        try:
            out.append('inner')
            raise TypeError('t')
        except ValueError:
            out.append('wrong')
        finally:
            out.append('inner-finally')
    except TypeError as e:
        out.append('outer:' + str(e))
    finally:
        out.append('outer-finally')
    return out


print(nested())


def return_value_evaluated_before_finally():
    x = [1]
    try:
        return x[:]
    finally:
        x.append(2)
        log.append(x)


print(return_value_evaluated_before_finally(), log)
log.clear()


def finally_return_in_loop():
    for i in range(3):
        try:
            return i
        finally:
            if i < 2:
                continue
    return 'end'


print(finally_return_in_loop())


def try_except_in_except():
    try:
        raise ValueError('a')
    except ValueError:
        try:
            raise KeyError('b')
        except KeyError as e:
            return 'inner caught %r' % (e,)


print(try_except_in_except())


def handler_order():
    res = []
    for exc in (ValueError, KeyError, IndexError, LookupError, ZeroDivisionError):
        try:
            raise exc('m')
        except KeyError:
            res.append('key')
        except LookupError:
            res.append('lookup')
        except (ValueError, ArithmeticError) as e:
            res.append('va:' + type(e).__name__)
    return res


print(handler_order())


def gen_counter():
    count = 0
    for i in range(5):
        try:
            try:
                if i % 2:
                    raise ValueError(i)
            finally:
                count += 10
        except ValueError:
            count += 1
    return count


print(gen_counter())

# try/finally at module level
try:
    print('module try')
finally:
    print('module finally')

for i in range(3):
    try:
        if i == 1:
            break
    finally:
        print('module loop finally', i)
