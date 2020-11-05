# How long does it take to find all executables?

import os
import shutil
import time

N = 100


def find_executables():
    """
    Finds a list of the executable.

    Args:
    """
    executable = []
    path = os.environ['PATH'].split(':')
    for p in path:
        for f in os.listdir(p):
            if shutil.which(f):
                executable.append(f)
    return executable


def main():
    """
    Main function.

    Args:
    """
    start = time.time()
    for i in range(N):
        find_executables()
    stop = time.time()
    average = 1000 * (stop - start) / N
    print('{} msec'.format(average))


main()