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

import types

import marcel.argsparser
import marcel.core


HELP = '''
{L,wrap=F}sort [KEY]

{L,indent=4:28}{r:KEY}                     The function to be applied to input tuples, to get the values by which tuples 
should be ranked.

The input stream is sorted and written to the output stream.

If a {r:KEY} is not specified, then input tuples are ordered according to Python rules.
Otherwise, ordering is based on the values computed by applying {r:KEY} to each input tuple.
'''


def sort(env, key=None):
    return Sort(env), [] if key is None else [key]


class SortArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('sort', env)
        self.add_anon('key', convert=self.function, default=None)
        self.validate()


class Sort(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.key = None
        self.contents = None

    def __repr__(self):
        return 'sort'

    # AbstractOp
    
    def setup(self):
        self.contents = []

    def set_env(self, env):
        super().set_env(env)
        if self.key:
            self.key.set_globals(env.vars())

    # Op

    def receive(self, x):
        # x is None occurs only for the first op in a pipeline. Sort shouldn't be used there, but whatever.
        # Fixes bug 10.
        if x is not None:
            self.contents.append(x)
    
    def receive_complete(self):
        if self.contents is not None:
            if self.key:
                self.contents.sort(key=(lambda t: self.call(self.key, *t)))
            else:
                self.contents.sort()
            for x in self.contents:
                self.send(x)
            self.contents = None
        self.send_complete()
