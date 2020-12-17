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

import pathlib

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.file


HELP = '''
{L,wrap=F}pushd [DIRECTORY]

{L,indent=4:28}{r:DIRECTORY}               The directory to be added to the directory stack.

Push The given {r:DIRECTORY} onto the directory stack, and cd to it.

If no {r:DIRECTORY} is supplied, then the top two items on the directory stack are swapped,
and the current directory is changed to the new top directory on the stack.
'''


def pushd(env, directory=None):
    return Pushd(env), [] if directory is None else [directory]


class PushdArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('pushd', env)
        self.add_anon('directory', convert=self.check_str, default=None)
        self.validate()


class Pushd(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.directory = None

    def __repr__(self):
        return f'pushd({self.directory})' if self.directory else 'pushd()'

    # AbstractOp

    def setup(self):
        if self.directory is not None:
            self.directory = pathlib.Path(self.directory).expanduser()

    def run(self):
        try:
            self.env().dir_state().pushd(self.directory)
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
