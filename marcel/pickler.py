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

import io
import sys

import dill

import marcel.util

PERSISTENT_CLASSES = set()


class Cached:

    def __init__(self):
        PERSISTENT_CLASSES.add(type(self))

    def id(self):
        assert False


class MarcelPickler(dill.Pickler):

    def __init__(self):
        self.buffer = io.BytesIO()
        super().__init__(self.buffer)

    def persistent_id(self, x):
        cls = type(x)
        if cls in PERSISTENT_CLASSES:
            return cls, x.id()
        else:
            return None

    def dump(self, x):
        self.buffer.seek(0)
        super().dump(x)


class MarcelUnpickler(dill.Unpickler):

    def __init__(self, buffer):
        assert buffer is not None
        super().__init__(buffer)
        self.buffer = buffer

    def persistent_load(self, pid):
        try:
            cls, id = pid
            return cls.reconstitute(id)
        except KeyError:
            assert False, pid

    def load(self):
        self.buffer.seek(0)
        return super().load()


def copy(x):
    try:
        pickler = MarcelPickler()
        unpickler = MarcelUnpickler(pickler.buffer)
        pickler.dump(x)
        copy = unpickler.load()
        return copy
    except Exception as e:
        sys.stdout.flush()
        print(f'Cloning error: ({type(e)}) {e}', file=sys.__stderr__, flush=True)
        marcel.util.print_stack(sys.__stderr__)
