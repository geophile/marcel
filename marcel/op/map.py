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
import marcel.util


HELP = '''
{L,wrap=F}[map] FUNCTION

{L,indent=4:28}{r:FUNCTION}                The function to be applied to each input tuple.

For each tuple in the input stream, apply the given {r:FUNCTION} and write the result to the output stream.

The components of an input tuple are bound to the {r:FUNCTION}'s parameters.

Note that the operator name, {r:map}, can be omitted. If you provide a {r:FUNCTION} by itself, it will be assumed that
the {r:map} operator was intended.
'''


def map(env, function):
    return Map(env), [] if function is None else [function]


class MapArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('map', env)
        self.add_anon('function', convert=self.function)
        self.validate()


class Map(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.function = None

    def __repr__(self):
        return f'map({self.function.snippet()})'

    # AbstractOp

    def set_env(self, env):
        super().set_env(env)
        self.function.set_globals(env.vars())

    # Op

    def run(self):
        self.send(self.call(self.function))
    
    def receive(self, x):
        self.send(self.call(self.function, *x))
