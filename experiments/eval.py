from time import *


G = 0


def inc(x):
    """
    Inc ( x

    Args:
        x: (int): write your description
    """
    global G
    G = x + 1
    return G


def direct_call(n):
    """
    Return the direct direct direct direct direct direct arguments.

    Args:
        n: (todo): write your description
    """
    f = inc
    x = 0
    start = time_ns()
    for i in range(n):
        x = f(x)
    stop = time_ns()
    assert x == n
    return (stop - start) / 1000000


def eval_call(n):
    """
    Evaluate n times.

    Args:
        n: (array): write your description
    """
    x = 0
    start = time_ns()
    for i in range(n):
        x = eval('inc(x)')
    stop = time_ns()
    assert x == n
    return (stop - start) / 1000000


def code_call(n):
    """
    Compiles and n times.

    Args:
        n: (todo): write your description
    """
    global G
    code = compile('inc(x)\n', '<string>', 'eval', optimize=2)
    x = 0
    start = time_ns()
    g = globals()
    l = {'x': 0}
    for i in range(n):
        l['x'] = eval(code, g, l)
    stop = time_ns()
    x = l['x']
    assert x == n, x
    print('G = ' + G)
    return (stop - start) / 1000000


N = 100000
direct_msec = direct_call(N)
eval_msec = eval_call(N)
code_msec = code_call(N)
eval_penalty = eval_msec / direct_msec
code_penalty = code_msec / direct_msec
print('direct: {} nsec per call'.format(direct_msec / N))
print('eval:   {} nsec per call, {} x slower than direct'.format(eval_msec / N, eval_penalty))
print('code:   {} nsec per call, {} x slower than direct'.format(code_msec / N, code_penalty))
