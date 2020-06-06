from marcel.api import *

negate = map(lambda x: -x)

print('ONE NEGATE')
run(gen(3) | negate)
print('TWO NEGATES')
run(gen(3) | negate | negate)