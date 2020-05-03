from marcel.api import *


def times(acc, x):
    return x if acc is None else acc * x


def plus(acc, x):
    return x if acc is None else acc + x


def cat(*x):
    return bash('cat', *x)


#
# run(gen(5) | map(lambda x: -x))
# run(ls('/home/jao/bin') | map(lambda f: (f.size, f.name)))
# run(gen(10, 1) | red(lambda acc, x: x if acc is None else acc * x))
# run(cat('/home/jao/cat_boarding.txt') | map(lambda x: x.split()))
#
#
# print(f'{only(gen(10) | red(plus))[0]}')

# for x, y in gather(gen(10) | map(lambda x: (x, x))):
#     print(f'{x}  {y}')

# print('\n'.join(gather(
#     ls('/home/jao/git/marcel', file=True, recursive=True) |
#     map(lambda f: (f.suffix.lower(), f.size)) |
#     red(None, plus) |
#     sort(lambda ext, size: -size) |
#     map(lambda ext, size: f'{ext}: {size}')
# )))

for x in gather(
        ls('/home/jao/git/marcel', file=True, recursive=True) |
        select(lambda f: f.suffix == '.py') |
        map(lambda f: (f, f)) |
        expand(1) |
        map(lambda f, line: (f, line.lower())) |
        select(lambda f, line: 'send' in line and 'error' in line)):
    print(x)
