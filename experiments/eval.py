from time import *


G = 0


def inc(x):
    global G
    G = x + 1
    return G


def direct_call(n):
    f = inc
    x = 0
    start = time_ns()
    for i in range(n):
        x = f(x)
    stop = time_ns()
    assert x == n
    return (stop - start) / 1000000


def eval_call(n):
    x = 0
    start = time_ns()
    for i in range(n):
        x = eval('inc(x)')
    stop = time_ns()
    assert x == n
    return (stop - start) / 1000000


def code_call(n):
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
    print('G = %s' % G)
    return (stop - start) / 1000000


N = 100000
direct_msec = direct_call(N)
eval_msec = eval_call(N)
code_msec = code_call(N)
eval_penalty = eval_msec / direct_msec
code_penalty = code_msec / direct_msec
print('direct: %s nsec per call' % (direct_msec / N))
print('eval:   %s nsec per call, %s x slower than direct' % (eval_msec / N, eval_penalty))
print('code:   %s nsec per call, %s x slower than direct' % (code_msec / N, code_penalty))
