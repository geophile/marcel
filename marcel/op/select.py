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


SUMMARY = '''
Tuples in the input stream are filtered using a predicate.
'''


DETAILS = '''
The {r:function} is applied to each input tuple. Tuples for which the {r:function} evalutes to
True are written to the output stream.
'''


def select(env, function):
    return Select(env), [] if function is None else [function]


class SelectArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('select', env)
        self.add_anon('function', convert=self.function)
        self.validate()


class Select(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.function = None

    def __repr__(self):
        return f'select({self.function.source()})'

    # BaseOp
    
    def receive(self, x):
        if self.function(*x):
            self.send(x)
