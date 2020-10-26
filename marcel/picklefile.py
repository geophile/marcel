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

import dill


class PickleFile:

    def __init__(self, path):
        self.path = path
        self.readers = {}  # id(PickleFile) -> Reader
        self.writers = {}  # id(PickleFile) -> Writer

    def __repr__(self):
        nr = len(self.readers)
        nw = len(self.writers)
        return (f'{self.__class__.__name__}({self.path})'
                if nr == 0 and nw == 0 else
                f'{self.__class__.__name__}({self.path}: readers = {nr}, writers = {nw})')

    def __iter__(self):
        return self.reader()

    def __enter__(self):
        return self.reader()

    def __exit__(self):
        self.close()
        return self

    def reader(self):
        reader = Reader(self)
        self.readers[id(self)] = reader
        return reader

    def writer(self, append):
        writer = Writer(self, append)
        self.writers[id(self)] = writer
        return writer

    def ensure_deleted(self):
        assert len(self.readers) == 0 and len(self.writers) == 0, self
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def close(self):
        self_id = id(self)
        try:
            access = self.readers.pop(self_id)
        except KeyError:
            try:
                access = self.writers.pop(self_id)
            except KeyError:
                access = None
        if access is not None:
            access.close_file()


class Access:

    def __init__(self, owner):
        self.owner = owner
        self.file = None

    def close(self):
        self.owner.close()

    def close_file(self):
        self.file.close()


class Reader(Access):

    def __init__(self, owner):
        super().__init__(owner)
        self.file = open(owner.path, 'r+b')

    def __next__(self):
        try:
            return self.read()
        except EOFError:
            self.close()
            raise StopIteration()
        except:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def read(self):
        return dill.load(self.file)


class Writer(Access):

    def __init__(self, owner, append):
        super().__init__(owner)
        self.file = open(owner.path, 'a+b' if append else 'w+b')

    def flush(self):
        self.file.flush()

    def write(self, x):
        try:
            dill.dump(x, self.file)
        except:
            self.close()
            raise
