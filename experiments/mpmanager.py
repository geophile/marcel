# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

from multiprocessing.managers import *
from multiprocessing import *
import os
import dill
import time
import random


def dump(label, x):
    """
    Prints the object

    Args:
        label: (str): write your description
        x: (todo): write your description
    """
    print(f'{label}: {x}')


class Env:

    def __init__(self):
        """
        Initialize the lock.

        Args:
            self: (todo): write your description
        """
        self.map = {}
        self.lock = Lock()

    def inc(self, k):
        """
        Increment the lock.

        Args:
            self: (todo): write your description
            k: (int): write your description
        """
        self.lock.acquire()
        v = self.map.get(k, 0) + 1
        self.map[k] = v
        self.lock.release()
        return v


class EnvManager(BaseManager):
    pass


EnvManager.register('Env', Env)


def hello(env_manager):
    """
    This function

    Args:
        env_manager: (todo): write your description
    """
    print(f'main: {os.getpid()}')
    env = env_manager.Env()
    env.setvar('a', 1)
    env.setvar('b', 'two')
    env.setvar('c', dill.dumps(lambda x: -x))
    a = env.getvar('a')
    b = env.getvar('b')
    c = dill.loads(env.getvar('c'))
    print(f'a: {a}, b: {b}, c(5): {c(5)}')
    N = 100000
    start = time.time()
    for i in range(N):
        env.getvar('a')
    stop = time.time()
    print(f'Time per getvar: {1000 * (stop - start) / N} msec')


TRIALS = 10


def hello_hello(env, N):
    """
    This function

    Args:
        env: (todo): write your description
        N: (todo): write your description
    """
    def ping_env(thread, rand, N):
        """
        Ping n times

        Args:
            thread: (todo): write your description
            rand: (todo): write your description
            N: (todo): write your description
        """
        print(f'{os.getpid()} -- ({type(env)}: {env}')
        for i in range(TRIALS):
            k = rand.randint(0, N-1)
            v = env.inc(k)
            print(f'{k}: {v: 4d} -- T{thread}')

    processes = []
    for thread in range(N):
        p = Process(target=ping_env, args=(thread, random.Random(), N))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


if __name__ == '__main__':
    with EnvManager() as env_manager:
        # hello(manager)
        env = env_manager.Env()
        print(f'{os.getpid()} -- ({type(env)}: {env}')
        hello_hello(env, 5)

# class C:
#
#     def __init__(self, x):
#         self.x = x
#
#     def __repr__(self):
#         return f'C({id(self)}, {self.x})'
#
#
# def f(d, l):
#     print(f'f: {os.getpid()}, {type(d)}, {type(l)}')
#     print('f before d', d)
#     print('f before l', l)
#     d[1] = '1'
#     d['2'] = 2
#     d[0.25] = None
#     l.reverse()
#     print('f after d', d)
#     print('f after l', l)
#
#
# if __name__ == '__main__':
#     with Manager() as manager:
#         d = manager.dict()
#         d['c'] = C(123)
#         l = manager.list(range(10))
#         print(f'main: {os.getpid()}, {type(d)}, {type(l)}')
#         print('main before d', d)
#         print('main before l', l)
#
#         p = Process(target=f, args=(d, l))
#         p.start()
#         p.join()
#
#         print('main after d', d)
#         print('main after l', l)
