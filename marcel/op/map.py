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


SUMMARY = '''
For each item in the input stream, apply a given function and write the result to the output stream.
'''


DETAILS = '''
The {r:function} is applied to each input tuple in the input stream. The components of a tuple
are bound to the {r:function}'s parameters. The output from the function is written to the output stream.
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
        return f'map({self.function.source()})'

    # BaseOp
    
    def receive(self, x):
        output = self.function() if x is None else self.function(*x)
        self.send(output)
