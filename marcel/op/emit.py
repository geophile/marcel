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


def emit(env):
    return Emit(env), []


class EmitArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('emit', env)
        self.validate()


class Emit(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.loop_op = None

    # AbstractOp

    def receive(self, x):
        # Send x outside the loop
        self.loop_op.send(x)
        # Send x down the pipeline inside the loop
        self.send(x)

    # Emit

    def set_loop_op(self, loop_op):
        self.loop_op = loop_op
