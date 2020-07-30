from marcel.api import *

run(cd('/home/jao/git/marcel'))
print(env.getvar('PWD'))
for ext, size in (ls('marcel', 'test', file=True, recursive=True) |
                  map(lambda f: (f.suffix, f.size)) |
                  red('.', '+')):
    print(f'{ext}: {size}')
