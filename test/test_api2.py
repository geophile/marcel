import os
from marcel.api import *

x = reservoir('x')
run(gen(10) | store(x))
run(load(x))