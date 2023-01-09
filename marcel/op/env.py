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
import marcel.object.error

HELP = '''
{L,wrap=F}env 
{L,wrap=F}env VAR
{L,wrap=F}env -d|--delete VAR
{L,wrap=F}env -p|--pattern PATTERN

{L,indent=4:28}{r:VAR}                     The name of an environment variable.

{L,indent=4:28}{r:-d}, {r:--delete}            Output the named variable and its value, and remove the variable 
from the environment.

{L,indent=4:28}{r:-p}, {r:--pattern}           Output symbols whose variable name contains the string {r:PATTERN}

Write some or all of the contents of the environment, (i.e., the marcel namespace), 
to the output stream.
Each variable/value pair is written to the output stream as a tuple,
(variable, value), sorted by variable. Python's {n:__builtins__} is part of the marcel namespace, but is always omitted
from output. 

If not arguments are provided, then all variables and their values are written to the output stream. 
Specifying just {r:VAR} outputs the one variable with that name. An error is output if the variable is not defined. 

Specifying {r:VAR} and {r:VALUE} assigns the value to the variable, and outputs the updated variable.

If the {r:--delete} flag is specified, the named variable and its current value
are written to output, and the variable
is removed from the environment.

If the {r:--pattern} flag is specified, then the variables output are those whose name contain the substring
{r:PATTERN}.
'''


def env(e, var=None, delete=None, pattern=None):
    args = []
    if delete:
        args.extend(['-d', delete])
    if pattern:
        args.extend(['-p', pattern])
    if var:
        args.append(var)
    return Env(e), args


class EnvArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('env', env)
        self.add_flag_one_value('delete', '-d', '--delete')
        self.add_flag_one_value('pattern', '-p', '--pattern')
        self.add_anon('var', default=None)
        self.at_most_one('delete', 'var', 'pattern')
        self.validate()


class Env(marcel.core.Op):
    OMITTED = ['__builtins__']

    def __init__(self, env):
        super().__init__(env)
        self.delete = None
        self.var = None
        self.pattern = None
        self.list_all = None

    def __repr__(self):
        return (f'env({self.var})' if self.var else
                f'env(delete {self.delete})' if self.delete else
                f'env(pattern {self.pattern})' if self.pattern else
                'env()')

    # AbstractOp

    def setup(self):
        self.list_all = self.var is None and self.delete is None and self.pattern is None

    def run(self):
        if self.var:
            self.one_var()
        elif self.delete:
            self.delete_var()
        elif self.pattern:
            self.matching_vars()
        else:
            self.all_vars()

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True

    # Implementation

    def one_var(self):
        assert self.var
        value = self.env().getvar(self.var)
        if value is None:
            self.no_such_var(self.var)
        else:
            self.send((self.var, value))

    def delete_var(self):
        assert self.delete
        value = self.env().delvar(self.delete)
        if value is None:
            self.no_such_var(self.var)
        else:
            self.send((self.delete, value))

    def matching_vars(self):
        assert self.pattern
        output = []
        for var, value in self.env().vars().items():
            if var != '__builtins__' and self.pattern in var:
                output.append((var, value))
        for var, value in sorted(output):
            self.send((var, value))

    def all_vars(self):
        output = []
        for var, value in self.env().vars().items():
            if var != '__builtins__':
                output.append((var, value))
        for var, value in sorted(output):
            self.send((var, value))

    def no_such_var(self, var):
        error = marcel.object.error.Error(f'{var} is undefined')
        self.send(error)