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
import marcel.reservoir


HELP = '''
{L,wrap=F}store [-a|--append] VAR
{L,wrap=F}> VAR
{L,wrap=F}>> VAR

{L,indent=4:28}{r:-a}, {r:--append}                     Append to {r:VAR}s list, instead of replacing.

{L,indent=4:28}{r:VAR}                     The variable to be updated.

Write the incoming tuples into a list bound to {r:VAR}. By default, the current value of {r:VAR}
is replaced. If {r:--append} is specified, then it is expected that the current value
of {r:VAR} is a list, and the incoming tuples are appended. 

There is special optional syntax for the {r:store} operator: {r:store VAR} can be written as {r:> VAR}. 
With this alternative syntax, the {r:>} acts as a pipe ({r:|}). So, for example, the following command:

{L,wrap=F}gen 5 | store x

stores the stream carrying {r:0, 1, 2, 3, 4} in variable {r:x}. This can also be written as:

{L,wrap=F}gen 5 > x

The symbol {r:>>} is used to append to the contents of the variable, instead of
replacing the value, e.g. {r:gen 5 >> x}. 
'''


def store(env, reservoir, append=False):
    store = Store(env)
    store.reservoir = reservoir
    args = []
    if append:
        args.append('--append')
    args.append(None)  # var
    return store, args


class StoreArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('store', env)
        self.add_flag_no_value('append', '-a', '--append')
        self.add_anon('var', convert=self.init_reservoir)
        self.validate()


class Store(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.append = None
        self.reservoir = None
        self.writer = None

    def __repr__(self):
        return f'store({self.var}, append)' if self.append else f'store({self.var})'

    # AbstractOp
    
    def setup_1(self, env):
        super().setup_1(env)
        if self.var is not None and self.reservoir is None:
            self.setup_interactive(env)
        elif self.var is None and self.reservoir is not None:
            self.setup_api()
        else:
            assert False
        env.mark_possibly_changed(self.var)

    def receive(self, x):
        try:
            self.writer.write(x)
        except:
            self.writer.close()
            raise

    def receive_complete(self):
        self.writer.close()
        self.send_complete()

    # For use by this class

    def setup_interactive(self, env):
        if not self.var.isidentifier():
            raise marcel.exception.KillCommandException(f'{self.var} is not a valid identifier')
        self.reservoir = self.getvar(env, self.var)
        self.prepare_reservoir(env)

    def setup_api(self):
        if self.reservoir is None:
            raise marcel.exception.KillCommandException(f'Accumulator is undefined.')
        self.prepare_reservoir(None)

    def description(self):
        return self.var if self.var else 'store\'s variable'

    def prepare_reservoir(self, env):
        if self.reservoir is None:
            self.reservoir = marcel.reservoir.Reservoir(self.var)
            env.setvar(self.var, self.reservoir)
        elif type(self.reservoir) is not marcel.reservoir.Reservoir:
            raise marcel.exception.KillCommandException(
                f'{self.description()} is not usable as a reservoir, '
                f'it stores a value of type {type(self.reservoir)}.')
        self.writer = self.reservoir.writer(self.append)
