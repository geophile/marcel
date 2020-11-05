from marcel.api import *


def fact(x):
    return (gen(x, 1) |
            args(lambda n: gen(n, 1) |
                           red(r_times) |
                           map(lambda f: (n, f))))


run(fact(50))
