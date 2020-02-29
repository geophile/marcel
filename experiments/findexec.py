# How long does it take to find all executables?

import os
import shutil
import time

N = 100


def find_executables():
    executable = []
    path = os.environ['PATH'].split(':')
    for p in path:
        for f in os.listdir(p):
            if shutil.which(f):
                executable.append(f)
    return executable


def main():
    start = time.time()
    for i in range(N):
        find_executables()
    stop = time.time()
    average = 1000 * (stop - start) / N
    print('{} msec'.format(average))


main()