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

import marcel.argsparser
import marcel.core
import marcel.exception

HELP = '''
{L,wrap=F}exit

Marcel exits.
'''


class ExitArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('exit', env)
        self.validate()


class Exit(marcel.core.Op):

    def __repr__(self):
        return 'exit'

    # AbstractOp

    def run(self, env):
        raise marcel.exception.ExitException()

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
