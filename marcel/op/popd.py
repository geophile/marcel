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
import marcel.object.file


HELP = '''
{L,wrap=F}popd

Pop the directory stack, and cd to the new top directory. The current directory stack is written to output.
'''


def popd(env):
    return Popd(env), []


class PopdArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('popd', env)
        self.validate()


class Popd(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)

    def __repr__(self):
        return 'popd()'

    # AbstractOp

    def run(self):
        try:
            self.env().dir_state().popd()
        except PermissionError as e:
            raise marcel.exception.KillCommandException(e)
        except FileNotFoundError as e:
            raise marcel.exception.KillCommandException(e)
        for dir in self.env().dir_state().dirs():
            self.send(marcel.object.file.File(dir))

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
