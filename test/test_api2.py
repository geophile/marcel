from marcel.api import *

M.env.namespace = globals()

even = []
run(gen(10) | ifthen(lambda x: x % 2 == 0, store(even)) | select(lambda *x: False))
run(load(even))
