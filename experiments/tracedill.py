import dill

from marcel.api import *


def main():
    p = gen(3) | write()
    dill.detect.trace(True)
    dill.dumps(p)

main()
