from marcel.api import *

even = []
odd = []
run(gen(10) | ifelse(lambda x: x % 2 == 0, store(even)) | store(odd))
run(load(even))
run(load(odd))
