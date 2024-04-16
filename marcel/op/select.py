# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
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
{L,wrap=F}select FUNCTION

{L,indent=4:28}{r:FUNCTION}                The function to be applied to each input tuple.

Tuples in the input stream are filtered using a predicate. 

The {r:FUNCTION} is applied to each input tuple. Tuples for which the {r:FUNCTION} evalutes to
True are written to the output stream.
'''


def select(function):
    return Select(), [] if function is None else [function]


class SelectArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('select', env)
        self.add_anon('function', convert=self.function)
        self.validate()


class Select(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return f'select({self.function.snippet()})'

    # AbstractOp

    def setup(self, env):
        env.set_function_globals(self.function)

    # Op

    def receive(self, env, x):
        fx = (self.call(env, self.function)
              if x is None else
              self.call(env, self.function, *x))
        if fx:
            self.send(env, x)
