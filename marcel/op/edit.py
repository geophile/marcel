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
Open an editor to edit the previous command.
'''


DETAILS = '''
The editor is specified by the {n:EDITOR} environment variable. On exiting the editor, the edited command
will be on the command line. (Hit enter to run the command, as usual.)
'''


def edit():
    return Edit()


class EditArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('edit', env, None, SUMMARY, DETAILS)
        self.add_argument('n',
                          nargs='?',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'),
                          help='The identifying number of a history command.')


class Edit(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.n = None
        self.editor = None
        self.tmp_file = None

    def __repr__(self):
        return 'edit()'

    # BaseOp

    def setup_1(self):
        if self.n is None:
            self.n = 0
        self.editor = os.getenv('EDITOR')
        if self.editor is None:
            raise marcel.exception.KillCommandException(
                'Specify editor in the EDITOR environment variable')
        _, self.tmp_file = tempfile.mkstemp(text=True)

    def receive(self, _):
        # Remove the edit command from history
        readline.remove_history_item(readline.get_current_history_length() - 1)
        length = readline.get_current_history_length()
        print(f'edit: length = {length}, n = {self.n}')
        # The last command (the one before edit) is the one of interest.
        command = readline.get_history_item(readline.get_current_history_length() - length + self.n + 1)  # 1-based
        assert command is not None
        with open(self.tmp_file, 'w') as output:
            output.write(command)
        edit_command = f'{self.editor} {self.tmp_file}'
        process = subprocess.Popen(edit_command,
                                   shell=True,
                                   executable='/bin/bash',
                                   universal_newlines=True)
        process.wait()
        with open(self.tmp_file, 'r') as input:
            command_lines = input.readlines()
        self.env().edited_command = ''.join(command_lines)
        os.remove(self.tmp_file)

    # Op

    def must_be_first_in_pipeline(self):
        return True
