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
{L,wrap=F}delete VAR ...

{L,indent=4:28}{r:VAR}                     A variable to be deleted from the environment.

Delete the named {r:VAR}s from the environment, (i.e., from the marcel namespace). 
'''


def delete(env, *vars):
    return Delete(env), [vars]


class DeleteArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('delete', env)
        self.add_anon_list('vars', target='vars_arg')
        self.validate()


class Delete(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.vars_arg = None
        self.vars = None

    def __repr__(self):
        return f'delete({self.vars})'

    # AbstractOp

    def setup(self):
        self.vars = self.eval_function('vars_arg', str)
        for var in self.vars:
            if var not in self.env().namespace:
                raise marcel.exception.KillCommandException(f'Variable {var} is not defined.')

    def run(self):
        for var in self.vars:
            self.env().delvar(var)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
