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
import marcel.picklefile
import marcel.reservoir

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

{L,wrap=F}gen 5 | store x

stores the stream carrying {r:0, 1, 2, 3, 4} in variable {r:x}. This can also be written as:

{L,wrap=F}gen 5 >$ x

The symbol {r:>>$} is used to append to the contents of the {r:VAR}, instead of
replacing the value, e.g. {r:gen 5 >>$ x}. 
'''


def store(env, var, append=False):
    store = Store(env)
    args = []
    if append:
        args.append('--append')
    if type(var) in (str, marcel.reservoir.Reservoir):
        args.append(var)
    else:
        raise marcel.exception.KillCommandException(f'{var} is not a Reservoir: {type(var)}')
    return store, args


class StoreArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('store', env)
        self.add_flag_no_value('append', '-a', '--append')
        # init_target actually creates the target file or reservoir if it doesn't exist. This would 
        # normally be done by setup. However, for commands that don't terminate for a while, (e.g. ls -r / > x),
        # we want the variable available immediately. This allows the long-running command to be run in background,
        # monitoring progress, e.g. x > tail 5.
        self.add_anon('var', convert=self.init_var)
        self.validate()


class Store(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.append = None
        self.picklefile = None
        self.writer = None
        self.nesting = None

    def __repr__(self):
        return f'store({self.var}, append)' if self.append else f'store({self.var})'

    # AbstractOp

    def setup(self):
        if type(self.var) is marcel.reservoir.Reservoir:
            # API
            self.picklefile = self.var
        elif type(self.var) is str:
            # API: string is a filename.
            # Interactive: string is a filename or environment variable name.
            if self.var.isidentifier():
                self.picklefile = self.getvar(self.var)
                if type(self.picklefile) is not marcel.reservoir.Reservoir:
                    if self.append:
                        raise marcel.exception.KillCommandException(
                            f'{self.var} is not usable as a reservoir, '
                            f'it stores a value of type {type(self.picklefile)}.')
                    else:
                        self.picklefile = marcel.reservoir.Reservoir(self.var)
                        self.env().setvar(self.var, self.picklefile)
                self.env().mark_possibly_changed(self.var)
            else:
                raise marcel.exception.KillCommandException(f'{self.var} is not a Python identifier.')
        elif self.var is None:
            raise marcel.exception.KillCommandException(f'Reservoir is undefined.')
        else:
            raise marcel.exception.KillCommandException(
                f'{self.var} is not usable as a reservoir, it stores a value of type {type(self.picklefile)}.')
        self.writer = self.picklefile.writer(self.append)
        self.nesting = self.env().vars().n_scopes()

    def receive(self, x):
        try:
            self.writer.write(x)
        except:
            self.writer.close()
            raise

    def cleanup(self):
        self.writer.close()
