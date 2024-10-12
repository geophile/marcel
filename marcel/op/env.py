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
import marcel.object.error

HELP = '''
{L,wrap=F}env [-o|--os]
{L,wrap=F}env [-o|--os] VAR
{L,wrap=F}env [-o|--os] -p|--pattern PATTERN
{L,wrap=F}env -d|--delete VAR

{L,indent=4:28}{r:VAR}                     The name of an environment variable.

{L,indent=4:28}{r:-o}, {r:--os}                Search the host OS environment, not marcel's.

{L,indent=4:28}{r:-d}, {r:--delete}            Output the named variable and its value, and remove the variable 
from the environment.

{L,indent=4:28}{r:-p}, {r:--pattern}           Output symbols whose variable name contains the string {r:PATTERN}

Write some or all of the contents of the environment, (i.e., the marcel namespace), 
to the output stream.
Each variable/value pair is written to the output stream as a tuple,
(variable, value), sorted by variable. 

If no arguments are provided, then all variables and their values are written to the output stream. 
Specifying just {r:VAR} outputs the one variable with that name. An error is written if the variable is not defined. 

A value cannot be assigned to a variable through this command, use assignment instead, e.g. {n:HELLO = hello}.

If the {r:--delete} flag is specified, the named variable and its current value
are written to output, and the variable
is removed from the environment.

If the {r:--pattern} flag is specified, then the variables output are those whose name contain the substring
{r:PATTERN}.

If {r:--os} is specified, then the host OS environment, (obtained by Python's os.environ) is searched instead of the 
marcel namespace. This option is incompatible with {r:--delete}.
'''


def env(var=None, delete=None, pattern=None, os=False):
    args = []
    if delete:
        args.extend(['-d', delete])
    if pattern:
        args.extend(['-p', pattern])
    if os:
        args.append('--os')
    if var:
        args.append(var)
    return Env(), args


class EnvArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('env', env)
        self.add_flag_one_value('delete', '-d', '--delete')
        self.add_flag_one_value('pattern', '-p', '--pattern')
        self.add_flag_no_value('os', '-o', '--os')
        self.add_anon('var', default=None)
        self.at_most_one('delete', 'var', 'pattern')
        self.at_most_one('delete', 'os')
        self.validate()


class Env(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.delete = None
        self.var = None
        self.pattern = None
        self.os = None
        self.list_all = None
        self.impl = None

    def __repr__(self):
        buffer = []
        if self.os:
            buffer.append('os')
        if self.delete:
            buffer.append(f'delete {self.delete}')
        if self.pattern:
            buffer.append(f'pattern {self.pattern}')
        if self.var:
            buffer.append(self.var)
        return f'env({", ".join(buffer)})'

    # AbstractOp

    def setup(self, env):
        self.list_all = self.var is None and self.delete is None and self.pattern is None
        self.impl = EnvOS(self) if self.os else EnvMarcel(self)

    def run(self, env):
        if self.var:
            self.impl.one_var(env)
        elif self.delete:
            self.impl.delete_var(env)
        elif self.pattern:
            self.impl.matching_vars(env)
        else:
            self.impl.all_vars(env)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True


class EnvImpl(object):

    def __init__(self, op):
        self.op = op

    def one_var(self, env):
        assert False

    def delete_var(self, env):
        assert False

    def matching_vars(self, env):
        assert False

    def all_vars(self, env):
        assert False

    def no_such_var(self, env, var):
        raise marcel.exception.KillCommandException(f'{var} is undefined')


class EnvMarcel(EnvImpl):

    def one_var(self, env):
        var = self.op.var
        value = env.getvar(var)
        if value is None:
            self.no_such_var(env, var)
        else:
            self.op.send(env, (var, value))

    def delete_var(self, env):
        try:
            delete = self.op.delete
            value = env.delvar(delete)
            self.op.send(env, (delete, value))
        except KeyError:
            pass

    def matching_vars(self, env):
        output = []
        for var, value in env.vars().items():
            if self.op.pattern in var:
                output.append((var, value))
        for var, value in sorted(output):
            self.op.send(env, (var, value))

    def all_vars(self, env):
        for var, value in sorted(env.vars().items()):
            self.op.send(env, (var, value))


class EnvOS(EnvImpl):

    def one_var(self, env):
        var = self.op.var
        value = os.environ.get(var, None)
        if value is None:
            self.no_such_var(env, var)
        else:
            self.op.send(env, (var, value))

    def delete_var(self, env):
        assert False  # Should have been ruled out during arg processing

    def matching_vars(self, env):
        for var, value in sorted(os.environ.items()):
            if self.op.pattern in var:
                self.op.send(env, (var, value))

    def all_vars(self, env):
        for var, value in sorted(os.environ.items()):
            self.op.send(env, (var, value))
