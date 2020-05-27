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

import functools
import types

import marcel.argsparser
import marcel.core
import marcel.functionwrapper
from marcel.reduction import r_plus

SUMMARY = '''
The components of each input tuple are reduced using a given function.
'''


DETAILS = '''
Each input sequence is reduced to a single value, using {r:function} to combine the values.
{r:function} is a binary function that can be used for reduction, e.g. {n:+}, {n:*}, {n:max}, {n:min}.

{b:Example:} If one of the inputs is the list {n:[1, 2, 3, 4]}, then:
{p,wrap=F}
    squish +

will generate {n:10}.

If no {r:function} is provided, then {n:+} is assumed.
'''


def squish(env, function=r_plus):
    return Squish(env), [] if function is None else [function]


class SquishArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('squish', env)
        self.add_anon('function', convert=self.function, default=None)
        self.validate()


class Squish(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.function = None

    def __repr__(self):
        return f'squish({self.function.source()})' if self.function else 'squish()'

    # BaseOp
    
    def setup_1(self):
        if self.function is None:
            self.function = marcel.functionwrapper.FunctionWrapper(source='+', globals=self.env().namespace)
        self.function.set_op(self)

    def receive(self, x):
        self.send(functools.reduce(self.function, x, None))
