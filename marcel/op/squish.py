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
    op = Squish(env)
    op.function = marcel.functionwrapper.FunctionWrapper(function=function)
    return op


class SquishArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('squish', env, None, SUMMARY, DETAILS)
        self.add_argument('function',
                          nargs='?',
                          type=super().constrained_type(self.check_function, 'not a valid function'),
                          help='Reduction function, applied to the components of an input tuple.')


class Squish(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.function = None

    def __repr__(self):
        return f'squish({self.function.source()})' if self.function else 'squish()'

    # BaseOp
    
    def setup_1(self):
        if self.function is None:
            self.function = marcel.functionwrapper.FunctionWrapper(source='+', globals=self.env().vars())
        self.function.set_op(self)

    def receive(self, x):
        self.send(functools.reduce(self.function, x, None))
