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


SUMMARY = '''
{L,wrap=F}delete VAR

{L,indent=4:28}{r:VAR}                     The variable to be deleted from the environment.

Delete {r:VAR} from the environment, (i.e., from the marcel namespace). 
'''


def delete(env, var):
    return Delete(env), [var]


class DeleteArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('delete', env)
        self.add_anon('var')
        self.validate()


class Delete(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None

    def __repr__(self):
        return f'delete({self.var})'

    # AbstractOp

    def setup_1(self):
        if self.var not in self.env().namespace:
            raise marcel.exception.KillCommandException(f'Variable {self.var} is not defined.')

    def receive(self, _):
        try:
            del self.env().namespace[self.var]
        except KeyError:
            # Shouldn't happen, since we checked in setup_1, but why not.
            pass

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
