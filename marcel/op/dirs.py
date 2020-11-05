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
import marcel.object.file


HELP = '''
{L}dirs [-c|--clear]

{L,indent=4:28}{r:-c}, {r:--clear}              Clear the directory stack, and then place the current
directory on it. 

Write the entries in the directory stack to the output stream, top first.
'''


def dirs(env, clear=None):
    """
    Return a directory.

    Args:
        env: (todo): write your description
        clear: (bool): write your description
    """
    return Dirs(env), [] if clear is None else ['--clear']


class DirsArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__('dirs', env)
        self.add_flag_no_value('clear', '-c', '--clear')
        self.validate()


class Dirs(marcel.core.Op):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env)
        self.clear = None

    def __repr__(self):
        """
        Return a repr representation of a repr__.

        Args:
            self: (todo): write your description
        """
        return f'dirs(clear={self.clear})'

    # AbstractOp

    def receive(self, _):
        """
        Receive the contents of the environment.

        Args:
            self: (todo): write your description
            _: (todo): write your description
        """
        if self.clear:
            self.env().dir_state().reset_dir_stack()
        for dir in self.env().dir_state().dirs():
            self.send(marcel.object.file.File(dir))

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
