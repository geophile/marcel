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

import os

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.picklefile
import marcel.reservoir
import marcel.util

Reservoir = marcel.reservoir.Reservoir

HELP = '''
{L,wrap=F}store [-a|--append] VAR
{L,wrap=F}>$ VAR
{L,wrap=F}>>$ VAR

{L,indent=4:28}{r:-a}, {r:--append}            Append to {r:VAR}s list, instead of replacing.

{L,indent=4:28}{r:VAR}                     A variable.

Write the incoming tuples to the {r:VAR}. 

{r:VAR} is an environment variable. 

By default, the current value of {r:VAR} is replaced. 
If {r:--append} is specified, then the incoming tuples are appended. The variable's value must have 
previously been assigned tuples from a stream.)

There is special syntax for the {r:store} operator: {r:store VAR} can be written as {r:>$ VAR}. 
With this alternative syntax, the {r:>$} acts as a pipe ({r:|}). So, for example, the following command:

{L,wrap=F}gen 5 | store f

stores the stream carrying {r:0, 1, 2, 3, 4} in variable {r:f}. This can also be written as:

{L,wrap=F}gen 5 >$ f

The symbol {r:>>$} is used to append to the contents of the {r:VAR}, instead of
replacing the value, e.g. {r:gen 5 >>$ f}. 
'''


def store(var, append=False):
    store = Store()
    args = []
    if append:
        args.append('--append')
    if marcel.util.one_of(var, (str, Reservoir)):
        args.append(var)
    else:
        raise marcel.exception.KillCommandException(f'{var} is not a Reservoir: {type(var)}')
    return store, args


class StoreArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('store', env)
        self.add_flag_no_value('append', '-a', '--append')
        self.add_anon('var')
        self.validate()


class Store(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.var = None
        self.append = None
        self.reservoir = None
        self.writer = None

    def __repr__(self):
        return f'store({self.var}, append)' if self.append else f'store({self.var})'

    # AbstractOp

    def setup(self, env):
        if type(self.var) is Reservoir:
            # API
            self.reservoir = self.var
        elif isinstance(self.var, str):
            # Interactive
            if self.var.isidentifier():
                value = env.getvar(self.var)
                if value is not None and type(value) is not Reservoir and self.append:
                    raise marcel.exception.KillCommandException(
                        f'A stream cannot be appended to {self.var} '
                        f'because it stores a value of type {type(value)}.')
                if type(value) is not Reservoir:
                    value = Reservoir(self.var, env.locations.data_ws_res(env.workspace, self.var))
                self.reservoir = value
                env.setvar(self.var, value)
                env.mark_possibly_changed(self.var)
            else:
                raise marcel.exception.KillCommandException(f'{self.var} is not a Python identifier.')
        elif self.var is None:
            raise marcel.exception.KillCommandException(f'Reservoir is undefined.')
        else:
            raise marcel.exception.KillCommandException(
                f'{self.var} is not usable as a reservoir, it stores a value of type {type(self.reservoir)}.')
        try:
            self.writer = self.reservoir.writer(append=self.append)
        except marcel.picklefile.PickleFileUsageError:
            raise marcel.exception.KillCommandException(f'store {self.var}: Pickle file already in use')

    def receive(self, env, x):
        try:
            self.writer.write(x)
        except:
            self.writer.close()
            raise

    def cleanup(self):
        self.writer.close()
