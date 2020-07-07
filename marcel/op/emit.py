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

import marcel.argsparser
import marcel.core

HELP = '''
{L,wrap=F}emit

This operator can only be used inside the pipeline of the {n:loop} operator.
Tuples arriving as input are written to the output stream, and are also
written to the output stream of the immediately enclosing {n:loop}. 
'''


def emit(env, function):
    return Emit(env), [function]


class EmitArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('emit', env)
        self.add_anon('function', convert=self.function)
        self.validate()


class Emit(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.function = None
        self.loop_op = None

    def __repr__(self):
        return f'emit({self.function})'

    # AbstractOp

    def receive(self, x):
        self.loop_op.send(self.function(*x))
        self.send(x)

    # Emit

    def set_loop_op(self, loop_op):
        self.loop_op = loop_op
