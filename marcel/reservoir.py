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

import os
import tempfile
import time

import dill

import marcel.pickler


DEBUG = False


# A Reservoir collects and feeds streams.

class Reservoir(marcel.pickler.Cached):

    CLOSED = -1
    READING = -2
    WRITING = -3

    def __init__(self, name, path=None):
        super().__init__()
        self.name = name
        if path:
            self.path = path
        else:
            _, self.path = tempfile.mkstemp()
        self.debug(f'init {self.path}')
        self.mode = Reservoir.CLOSED

    def __repr__(self):
        return f'Reservoir({self.name})'

    def __iter__(self):
        return self.reader()

    def id(self):
        return self.name, self.path

    @classmethod
    def reconstitute(cls, id):
        name, path = id
        return Reservoir(name, path)

    def reader(self):
        return Reader(self)

    def writer(self, append):
        return Writer(self, append)

    def ensure_deleted(self):
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def debug(self, message):
        if DEBUG:
            print(f'{os.getpid()} {self}: {message}')


class Reader:

    def __init__(self, reservoir):
        self.file = open(reservoir.path, 'r+b')

    def __next__(self):
        try:
            return self.read()
        except EOFError:
            self.close()
            raise StopIteration()
        except:
            self.close()
            raise

    def read(self):
        return dill.load(self.file)

    def close(self):
        self.file.close()


class Writer:

    FLUSH_INTERVAL_SEC = 1

    def __init__(self, reservoir, append):
        self.file = open(reservoir.path, 'a+b' if append else 'w+b')
        self.last_flush = time.time()

    def write(self, x):
        try:
            dill.dump(x, self.file)
            t = time.time()
            if t - self.last_flush > Writer.FLUSH_INTERVAL_SEC:
                self.file.flush()
                self.last_flush = t
        except:
            self.close()
            raise

    def close(self):
        self.file.close()

