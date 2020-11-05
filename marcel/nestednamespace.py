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

# A bracketed Python expression on the commandline is turned into a function by eval(source, namespace).
# The namespace implementation must implement nesting, to support pipeline args. Based on experiments/dict_subclass,
# function evaluation uses __getitem__. Defining __setitem__ seems to make a mess of pickling, so it's important
# to avoid overriding it.
#
# A NestedNamespace is a dict (superclass) and the set of params defined in that scope (introduced by a
# parameterized pipeline). scopes are outer namespaces, so scopes[0] is the namespace containing the current one,
# and scope[-1] is the topmost namespace, (the marcel namespace).

class NestedNamespace(dict):

    def __init__(self, map):
        """
        Initialize the map.

        Args:
            self: (todo): write your description
            map: (callable): write your description
        """
        super().__init__(map)
        self.scopes = []
        self.params = set(map.keys())

    def __repr__(self):
        """
        Return a representation of this object.

        Args:
            self: (todo): write your description
        """
        return str(self.flattened())

    def n_scopes(self):
        """
        Return the number of the scopes.

        Args:
            self: (todo): write your description
        """
        return len(self.scopes) + 1

    def push_scope(self, map):
        """
        Push a new scope to the scope.

        Args:
            self: (todo): write your description
            map: (array): write your description
        """
        if map is None:
            map = {}
        assert type(map) is dict, type(map)
        copy = NestedNamespace(self)
        copy.scopes = None
        self.params = set(map.keys())
        self.update(map)
        self.scopes.append(copy)

    def pop_scope(self):
        """
        Removes the current scopes.

        Args:
            self: (todo): write your description
        """
        assert len(self.scopes) > 0
        # Remove keys from this scope
        for key in self.params:
            try:
                self.pop(key)
            except KeyError:
                assert False, key
        # Restore outer scope
        scope = self.scopes.pop()
        updated_map = scope.copy()
        updated_map.update(self)
        self.clear()
        self.update(updated_map)
        self.params = scope.params

    def flattened(self):
        """
        Returns a copy of this : class.

        Args:
            self: (array): write your description
        """
        flattened = self.copy()
        for map in self.scopes:
            flattened.update(map)
        flattened.update(self)
        return flattened
