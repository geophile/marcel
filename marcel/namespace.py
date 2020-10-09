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

NOT_PROVIDED = object()


class NamespaceNotImplemented(Exception):

    def __init__(self, message, args, kwargs):
        super().__init__(f'{message}: args={args}, kwargs={kwargs}')


class NamespaceFrame:

    def __init__(self, map, outer):
        self.map = map
        self.outer = outer

    def getitem(self, key):
        try:
            return self.map[key]
        except KeyError:
            if self.outer is not None:
                return self.outer.getitem(key)
            else:
                raise

    def setitem(self, key, value):
        # Return true if the key was set, false otherwise.
        def set(frame, key, value):
            if key in frame.map:
                frame.map[key] = value
                return True
            elif frame.outer is not None:
                return set(frame.outer, key, value)
            else:
                return False
        # Have to find if the key exists anywhere before setting it.
        if not set(self, key, value):
            self.map[key] = value

    def delitem(self, key):
        def delete(frame, key):
            try:
                return frame.map.pop(key)
            except KeyError:
                if frame.outer is not None:
                    return delete(frame.outer, key)
                else:
                    raise
        return delete(self, key)

    def flattened(self):
        if self.outer is not None:
            flattened = self.outer.flattened()
            flattened.update(self.map)
            return flattened
        else:
            return self.map.copy()


class Namespace(dict):

    # dict -- overridden

    def __init__(self, map):
        super().__init__()
        self.innermost = NamespaceFrame(map, None)

    def __repr__(self, *args, **kwargs):
        if self.innermost is None:
            return 'Namespace(None -- BROKEN)'
        assert self.innermost is not None
        buffer = []
        f = self.innermost
        i = 0
        while f:
            buffer.append(f'{i}: {f.map}')
            i += 1
            f = f.outer
        return '\n'.join(buffer)

    def __getitem__(self, key):
        assert self.innermost is not None
        return self.innermost.getitem(key)

    def __setitem__(self, key, value):
        assert self.innermost is not None
        return self.innermost.setitem(key, value)

    def __delitem__(self, key):
        assert self.innermost is not None
        return self.innermost.delitem(key)

    def __contains__(self, key):
        assert self.innermost is not None
        try:
            self.innermost.getitem(key)
            return True
        except KeyError:
            return False

    def get(self, key, default=None):
        assert self.innermost is not None
        try:
            return self.innermost.getitem(key)
        except KeyError:
            return default

    def __eq__(self, other):
        assert self.innermost is not None
        return self.innermost.flattened() == other if self.innermost is not None else len(other) == 0

    def __ne__(self, other):
        assert self.innermost is not None
        return not self.__eq__(other)

    def keys(self):
        assert self.innermost is not None
        return self.innermost.flattened().keys()

    def update(self, map=None, **kwargs):
        assert self.innermost is not None
        if map is None:
            map = kwargs
        for key, value in map.items():
            self.innermost.setitem(key, value)

    def values(self):
        assert self.innermost is not None
        return self.innermost.flattened().values()

    def items(self):
        assert self.innermost is not None
        return self.innermost.flattened().items()

    def pop(self, key, default=NOT_PROVIDED):
        assert self.innermost is not None
        try:
            return self.innermost.delitem(key)
        except KeyError:
            if default is NOT_PROVIDED:
                raise
            else:
                return default

    # dict -- may need to override

    # def __delattr__(self, *args, **kwargs):
    #     raise NamespaceNotImplemented('__delattr__')

    def __dir__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__dir__', args, kwargs)

    def __doc__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__doc__', args, kwargs)

    def __format__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__format__', args, kwargs)

    def __ge__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__ge__', args, kwargs)

    def __gt__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__gt__', args, kwargs)

    def __hash__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__hash__', args, kwargs)

    def __init_subclass__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__init_subclass__', args, kwargs)

    def __iter__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__iter__', args, kwargs)

    def __le__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__le__', args, kwargs)

    def __len__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__len__', args, kwargs)

    def __lt__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__lt__', args, kwargs)

    def __reduce__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__reduce__', args, kwargs)

    def __reduce_ex__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__reduce_ex__', args, kwargs)

    def __reversed__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__reversed__', args, kwargs)

    # def __setattr__(self, *args, **kwargs):
    #     raise NamespaceNotImplemented('__setattr__', args, kwargs)

    def __sizeof__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__sizeof__', args, kwargs)

    def __str__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__str__', args, kwargs)

    def __subclasshook__(self, *args, **kwargs):
        raise NamespaceNotImplemented('__subclasshook__', args, kwargs)

    def clear(self, *args, **kwargs):
        raise NamespaceNotImplemented('clear', args, kwargs)

    def copy(self, *args, **kwargs):
        raise NamespaceNotImplemented('copy', args, kwargs)

    def fromkeys(self, *args, **kwargs):
        raise NamespaceNotImplemented('fromkeys', args, kwargs)

    def popitem(self, *args, **kwargs):
        raise NamespaceNotImplemented('popitem', args, kwargs)

    def setdefault(self, *args, **kwargs):
        raise NamespaceNotImplemented('setdefault', args, kwargs)

    # Namespace

    def frames(self):
        assert self.innermost is not None
        n = 0
        frame = self.innermost
        while frame:
            n += 1
            frame = frame.outer
        return n

    def push_frame(self, map):
        assert type(map) is dict
        self.innermost = NamespaceFrame(map, self.innermost)

    def pop_frame(self):
        assert self.innermost is not None
        assert self.innermost.outer is not None
        self.innermost = self.innermost.outer

    def flattened(self):
        return self.innermost.flattened()