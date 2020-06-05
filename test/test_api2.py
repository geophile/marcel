from marcel.api import *

zero = 0
run(gen(4) | red(lambda acc, x: x if acc is None else acc + x + zero))
