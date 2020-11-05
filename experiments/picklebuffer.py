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
        """
        Initialize the protocol.

        Args:
            self: (todo): write your description
            buffer: (todo): write your description
            protocol: (todo): write your description
        """
        super().__init__(buffer, protocol=protocol)
        self.buffer = buffer

    def persistent_id(self, x):
        """
        Persist a persistent identifier

        Args:
            self: (todo): write your description
            x: (todo): write your description
        """
        print(f'{x} -> {id(x)}')
        return id(x) if type(x) is C else None

    def dump(self, x):
        """
        Write the buffer.

        Args:
            self: (todo): write your description
            x: (todo): write your description
        """
        self.buffer.seek(0)
        super().dump(x)


class CustomUnpickler(dill.Unpickler):

    def __init__(self, buffer):
        """
        Initialize the buffer.

        Args:
            self: (todo): write your description
            buffer: (todo): write your description
        """
        super().__init__(buffer)
        self.buffer = buffer

    def persistent_load(self, pid):
        """
        Persist a persistent persistent persistent identifier.

        Args:
            self: (todo): write your description
            pid: (todo): write your description
        """
        x = C_CACHE.get(pid, None)
        print(f'{id(x)} -> {x}')
        return x

    def load(self):
        """
        Load the buffer.

        Args:
            self: (todo): write your description
        """
        self.buffer.seek(0)
        return super().load()


class C:

    def __init__(self, value):
        """
        Initializes the value

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self.value = value
        C_CACHE[id(self)] = self

    def __repr__(self):
        """
        Return a repr representation of a repr__.

        Args:
            self: (todo): write your description
        """
        return f'C({self.value})'


def hexid(x):
    """
    Return the hexadecimal hex string.

    Args:
        x: (todo): write your description
    """
    return hex(id(x))


def dump(label, x):
    """
    Pretty print a list of objects.

    Args:
        label: (str): write your description
        x: (todo): write your description
    """
    def _indent(level):
        """
        Indent the indentation.

        Args:
            level: (str): write your description
        """
        return '    ' * level
    def _dump(x, level, buffer):
        """
        Dump a list of objects.

        Args:
            x: (todo): write your description
            level: (int): write your description
            buffer: (todo): write your description
        """
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
    """
    Copy a pickler into a pickle.

    Args:
        x: (todo): write your description
    """
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
