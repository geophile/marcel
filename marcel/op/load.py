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
{L,wrap=F}load VAR

{L,indent=4:28}{r:VAR}                     The variable containing data to be loaded.

Write the conents of {r:VAR} to the output stream.  
'''


def load(env, accumulator):
    load = Load(env)
    load.accumulator = accumulator
    return load, [None]


class LoadArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('load', env)
        self.add_anon('var')
        self.validate()


class Load(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.accumulator = None
        self.input = None

    def __repr__(self):
        return f'load({self.var})'

    # AbstractOp
    
    def setup_1(self):
        # API: var is None, accumulator is set
        # Interactive: var is set, accumulator is None
        if self.var is not None:
            self.accumulator = self.env().getvar(self.var)
            if self.accumulator is None:
                raise marcel.exception.KillCommandException(f'Variable {self.var} is undefined.')
        else:
            if self.accumulator is None:
                raise marcel.exception.KillCommandException(f'Accumulator is undefined.')
        try:
            self.input = iter(self.accumulator)
        except:
            raise marcel.exception.KillCommandException(
                f'{self.var if self.var else "Accumulator"} is not iterable.')

    def receive(self, _):
        try:
            while True:
                self.send(next(self.input))
        except StopIteration:
            pass

    def must_be_first_in_pipeline(self):
        return True
