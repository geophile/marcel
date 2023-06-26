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
import marcel.op.filenames


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
        self.add_anon('directory', convert=self.check_str_or_file, default=None, target='directory_arg')
        self.validate()


class Pushd(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.directory_arg = None
        self.directory = None

    def __repr__(self):
        return f'pushd({self.directory})' if self.directory else 'pushd()'

    # AbstractOp

    def setup(self):
        dir_arg = self.eval_function('directory_arg', str, pathlib.Path, pathlib.PosixPath, marcel.object.file.File)
        if dir_arg is None:
            self.directory = None
        else:
            dirs = marcel.op.filenames.Filenames(self.env(), [pathlib.Path(dir_arg)]).normalize()
            if len(dirs) == 0:
                raise marcel.exception.KillCommandException('No qualifying path')
            elif len(dirs) > 1:
                raise marcel.exception.KillCommandException('Too many paths')
            self.directory = dirs[0]

    def run(self):
        try:
            self.env().dir_state().pushd(self.directory)
        except PermissionError as e:
            raise marcel.exception.KillCommandException(e)
        except FileNotFoundError as e:
            raise marcel.exception.KillCommandException(e)
        for dir in self.env().dir_state().dirs():
            self.send(marcel.object.file.File(dir))
