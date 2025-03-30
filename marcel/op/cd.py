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

import pathlib

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.file
import marcel.op.filenames

HELP = '''
{L}cd [DIRECTORY]

{L,indent=4:28}{r:DIRECTORY}               The new current directory.

Change the current directory to the given directory.
If {r:DIRECTORY} is omitted, then change the current directory to the home directory.
'''


def cd(directory=None):
    return Cd(), [] if directory is None else [directory]


class CdArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('cd', env)
        self.add_anon('directory', convert=self.check_str_or_file, default='~', target='directory_arg')
        self.validate()


class Cd(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.directory_arg = None
        self.directory = None

    def __repr__(self):
        return f'cd({self.directory})'

    # AbstractOp

    def setup(self, env):
        dir_arg = pathlib.Path(self.eval_function(env,
                                                  'directory_arg',
                                                  str, pathlib.Path, pathlib.PosixPath, marcel.object.file.File))
        try:
            dirs = marcel.op.filenames.Filenames(env, [dir_arg]).normalize()
        except Exception as e:
            raise marcel.exception.KillCommandException(f'Invalid argument: {dir_arg}: {str(e)}')
        if len(dirs) == 0:
            raise marcel.exception.KillCommandException('No qualifying path')
        elif len(dirs) > 1:
            raise marcel.exception.KillCommandException('Too many paths')
        elif not dirs[0].is_dir():
            raise marcel.exception.KillCommandException(f'{dirs[0]} is not a directory')
        self.directory = dirs[0]

    def run(self, env):
        try:
            env.dir_state().change_current_dir(self.directory)
        except PermissionError as e:
            raise marcel.exception.KillCommandException(e)
        except FileNotFoundError as e:
            raise marcel.exception.KillCommandException(e)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
