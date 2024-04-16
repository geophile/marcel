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

import marcel.argsparser
import marcel.core

HELP = '''
{L,wrap=F}reverse

The input stream is output in reverse order.
'''


def reverse():
    return Reverse(), []


class ReverseArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('reverse', env)
        self.validate()


class Reverse(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.contents = []

    # AbstractOp

    def receive(self, env, x):
        self.contents.append(x)

    def flush(self, env):
        if self.contents is not None:
            self.contents.reverse()
            for x in self.contents:
                self.send(env, x)
            self.contents = None
        self.propagate_flush(env)
