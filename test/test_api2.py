from marcel.api import *

run(bash('echo', 'hello', 'world'))
run(bash('echo', 'hello  world'))

# run(ls())
#
# # run
# run(gen(3))
#
# # gather
# print(gather(gen(3)))
#
# # first
# print(first(gen(start=100, count=10)))
#
# # iterator
# for x in gen(3, start=5):
#     print(x)
#
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
#
# for x in gen(3, -1) | map(lambda x: 1/x):
#     print(x)
#
# # # first with exception
# # print(first(map(lambda: 1 / 0)))
