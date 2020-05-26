from marcel.api import *
import time

# cat = map(lambda f: (f, f.readlines())) | expand(1)
# for f, line in ls('/home/jao/*.txt', file=True, recursive=True) | cat:
#     print(f'{f}: {line}')

# run(remote('jao', gen(3)))

# for ext, count, size in (ls('/home/jao/git/marcel', file=True, recursive=True)
#                          | map(lambda f: (f.suffix.lower(), 1, f.size))
#                          | red(None, r_plus, r_plus)
#                          | sort(lambda ext, count, size: -size)
#                          | head(10)):
#     print(f'{ext}: {size / count}')
#
# for size, pid, commandline in (ps(command='python')
#                                | sort(lambda p: p.VmRSS)
#                                | map(lambda p: (p.VmRSS, p.pid, p.commandline))):
#     print(f'{size} -- {pid}: {commandline}')

# import time
#
#
# def f(x):
#     return x + 1
#
#
# def call():
#     sum = 0
#     for i in range(1000000):
#         sum += f(i)
#     return sum
#
#
# def call_with_try():
#     sum = 0
#     for i in range(5000000):
#         try:
#             sum += f(i)
#         except Exception:
#             print('oops')
#     return sum
#
#
# for i in range(5):
#     call()
#     call_with_try()
#
# N = 5
#
# start = time.time()
# for i in range(N):
#     call()
# stop = time.time()
# print(f'call: {((stop - start) * 1000000)/ N} usec per call')
#
# start = time.time()
# for i in range(N):
#     call_with_try()
# stop = time.time()
# print(f'call_with_try: {((stop - start) * 1000000)/ N} usec per call')
