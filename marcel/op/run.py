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

import os
import readline
import subprocess
import tempfile

import marcel.core
import marcel.exception
import marcel.main


SUMMARY = '''
Run a previous command.
'''


DETAILS = '''
If {r:n} is not specified, then run the previous command. Otherwise, run the specified command.
The recalled command will replace {n:run} in the command history.
'''


def run():
    return Run()


class EditArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('run', env, None, SUMMARY, DETAILS)
        self.add_argument('n',
                          nargs='?',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'),
                          help='The identifying number of a history command.')


class Run(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.n = None
        self.editor = None
        self.tmp_file = None

    def __repr__(self):
        return 'edit()'

    # BaseOp

    def setup_1(self):
        pass

    def receive(self, _):
        # Remove the run command from history
        readline.remove_history_item(readline.get_current_history_length() - 1)
        length = readline.get_current_history_length()
        if self.n is None:
            self.n = length - 1
        # The last command (the one before edit) is the one of interest.
        self.env().edited_command = readline.get_history_item(
            readline.get_current_history_length() - length + self.n + 1)  # 1-based

    # Op

    def must_be_first_in_pipeline(self):
        return True
