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
import marcel.op.ifbase
import marcel.util


HELP = '''
TBD
'''


def ifthen(env, predicate, then):
    return Ifthen(env), [predicate, then.create_pipeline()]


class IfthenArgsParser(marcel.op.ifbase.IfBaseArgsParser):

    def __init__(self, env):
        super().__init__(env, 'ifthen')


class Ifthen(marcel.op.ifbase.IfBase):

    def __init__(self, env):
        super().__init__(env)

    # AbstractOp

    def receive(self, x):
        if self.predicate(*x):
            self.then.receive(x)
        self.send(x)
