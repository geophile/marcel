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
import marcel.exception


HELP = '''
{L,wrap=F}store VAR

{L,indent=4:28}{r:VAR}                     The variable to be updated.

Write the incoming tuples into a list bound to {r:VAR}.  
'''


def store(env, accumulator):
    store = Store(env)
    store.accumulator = accumulator
    return store, [None]


class StoreArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('store', env)
        self.add_anon('var')
        self.validate()


class Store(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.accumulator = None

    def __repr__(self):
        return f'store({self.var})'

    # AbstractOp
    
    def setup_1(self):
        # API: var is None, accumulator is set
        # Interactive: var is set, accumulator is None
        if self.var is not None:
            self.accumulator = self.getvar(self.var)
            if self.accumulator is None:
                self.accumulator = []
                self.env().setvar(self.var, self.accumulator)
        else:
            if self.accumulator is None:
                raise marcel.exception.KillCommandException(f'Accumulator is undefined.')
        if type(self.accumulator) is not list:
            raise marcel.exception.KillCommandException(
                f'{self.var if self.var else "Accumulator"} is not a list')

    def receive(self, x):
        self.send(x)
        self.accumulator.append(x)
