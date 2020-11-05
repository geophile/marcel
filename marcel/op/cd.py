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


HELP = '''
{L}cd [DIRECTORY]

{L,indent=4:28}{r:DIRECTORY}               The new current directory.

Change the current directory to the given directory.
If {r:DIRECTORY} is omitted, then change the current directory to the home directory.
'''


def cd(env, directory=None):
    """
    Return the directory.

    Args:
        env: (todo): write your description
        directory: (str): write your description
    """
    return Cd(env), [] if directory is None else [directory]


class CdArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__('cd', env)
        self.add_anon('directory', convert=self.check_str, default='~')
        self.validate()


class Cd(marcel.core.Op):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env)
        self.directory = None

    def __repr__(self):
        """
        Return a repr representation of a repr__.

        Args:
            self: (todo): write your description
        """
        return f'cd({self.directory})'

    # AbstractOp

    def setup(self,):
        """
        Sets the directory.

        Args:
            self: (todo): write your description
        """
        self.directory = pathlib.Path(self.directory)

    def receive(self, _):
        """
        Receive the environment to - receive.

        Args:
            self: (todo): write your description
            _: (todo): write your description
        """
        try:
            self.env().dir_state().cd(self.directory)
        except PermissionError as e:
            raise marcel.exception.KillCommandException(e)
        except FileNotFoundError as e:
            raise marcel.exception.KillCommandException(e)

    # Op

    def must_be_first_in_pipeline(self):
        """
        Returns true if the pipeline is in the pipeline.

        Args:
            self: (todo): write your description
        """
        return True

    def run_in_main_process(self):
        """
        Runs a list of - main loop.

        Args:
            self: (todo): write your description
        """
        return True
