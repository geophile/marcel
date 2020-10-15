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


def raise_not_a_reservoir(reservoir_description, type):
    raise marcel.exception.KillCommandException(
        f'{reservoir_description} is not usable as a reservoir, it stores a value of type {type}.')


def store(env, reservoir, append=False):
    store = Store(env)
    store.api = True
    store.reservoir = reservoir
    args = []
    if append:
        args.append('--append')
    if type(reservoir) is not marcel.reservoir.Reservoir:
        raise_not_a_reservoir(str(reservoir), type(reservoir))
    args.append(reservoir.name)
    return store, args


class StoreArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('store', env)
        self.add_flag_no_value('append', '-a', '--append')
        # init_reservoir actually creates the Reservoir if it doesn't exist. This would normally be done by
        # setup. However, for commands that don't terminate for a while, (e.g. ls / > x), we want the
        # variable available immediately. This allows the long-running command to be run in background,
        # monitoring progress, e.g. x > tail 5.
        self.add_anon('var', convert=self.init_reservoir)
        self.validate()


class Store(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.append = None
        self.reservoir = None
        self.writer = None
        self.api = False

    def __repr__(self):
        return f'store({self.var}, append)' if self.append else f'store({self.var})'

    # AbstractOp

    def setup(self):
        if self.api:
            self.setup_api()
        else:
            self.setup_interactive()
        self.env().mark_possibly_changed(self.var)

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

    def setup_interactive(self):
        if not self.var.isidentifier():
            raise marcel.exception.KillCommandException(f'{self.var} is not a valid identifier')
        self.reservoir = self.getvar(self.var)
        assert self.reservoir is not None  # See comment on StoreArgsParser.
        self.prepare_reservoir(self.env())

    def setup_api(self):
        if self.reservoir is None:
            raise marcel.exception.KillCommandException(f'Reservoir is undefined.')
        if type(self.reservoir) is not marcel.reservoir.Reservoir:
            raise_not_a_reservoir(self.description(), type(self.reservoir))
        self.prepare_reservoir(None)

    def description(self):
        return self.var if self.var else 'store\'s variable'

    def prepare_reservoir(self, env):
        if self.append and type(self.reservoir) is not marcel.reservoir.Reservoir:
            raise_not_a_reservoir(self.description(), type(self.reservoir))
        self.writer = self.reservoir.writer(self.append)

