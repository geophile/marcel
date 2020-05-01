from marcel.api import *

execute(gen(5) | map(lambda x: -x))

execute(ls('/home/jao/bin') | map(lambda f: (f.size, f.name)))
