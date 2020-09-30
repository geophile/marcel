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
import pickle
import dill


C_CACHE = {}


class CustomPickler(dill.Pickler):

    def __init__(self, buffer, protocol):
        super().__init__(buffer, protocol=protocol)
        self.buffer = buffer

    def persistent_id(self, x):
        print(f'{x} -> {id(x)}')
        return id(x) if type(x) is C else None

    def dump(self, x):
        self.buffer.seek(0)
        super().dump(x)


class CustomUnpickler(dill.Unpickler):

    def __init__(self, buffer):
        super().__init__(buffer)
        self.buffer = buffer

    def persistent_load(self, pid):
        x = C_CACHE.get(pid, None)
        print(f'{id(x)} -> {x}')
        return x

    def load(self):
        self.buffer.seek(0)
        return super().load()


class C:

    def __init__(self, value):
        self.value = value
        C_CACHE[id(self)] = self

    def __repr__(self):
        return f'C({self.value})'


def hexid(x):
    return hex(id(x))


def dump(label, x):
    def _indent(level):
        return '    ' * level
    def _dump(x, level, buffer):
        indent = _indent(level)
        if type(x) is list:
            buffer.append(f'{indent}{hexid(x)} [')
            for y in x:
                _dump(y, level + 1, buffer)
            buffer.append(f'{indent}]')
        else:
            buffer.append(f'{indent}{hexid(x)}: {x}')
    buffer = []
    _dump(x, 0, buffer)
    output = '\n'.join(buffer)
    print(f'{label}:')
    print(output)


def copy(x):
    buffer = io.BytesIO()
    pickler = CustomPickler(buffer, protocol=pickle.DEFAULT_PROTOCOL)
    pickler.dump(x)
    buffer.seek(0)
    unpickler = CustomUnpickler(buffer)
    return unpickler.load()


c = C(419)
x = [1, 999, c, 'foo bar', [1, 666, 777, 888, c]]
dump('original', x)
dump('copy', copy(x))
