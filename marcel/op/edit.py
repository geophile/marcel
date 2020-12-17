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

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.main


HELP = '''
{L,wrap=F}edit [COMMAND]

{L,indent=4:28}{r:COMMAND}                 The number of the command to be edited.

Open an editor to edit the command identified by {r:COMMAND} in the command history,
(obtained by running the {n:history} operator). I {r:COMMAND} is omitted, the most recently
executed command will be edited. The editor is selected by the {n:EDITOR}
environment variable. On exiting the editor, the edited command
will be on the command line. (Hit enter to run the command, as usual.)
'''


def edit(env, n=None):
    return Edit(env), [] if n is None else [n]


class EditArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('edit', env)
        self.add_anon('n', convert=self.str_to_int, default=None)
        self.validate()


class Edit(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.n = None
        self.editor = None
        self.tmp_file = None

    def __repr__(self):
        return 'edit()'

    # AbstractOp

    def setup(self):
        self.editor = self.env().getvar('EDITOR')
        if self.editor is None:
            raise marcel.exception.KillCommandException(
                'Specify editor in the EDITOR environment variable')
        _, self.tmp_file = tempfile.mkstemp(text=True)

    def run(self):
        # Remove the edit command from history
        readline.remove_history_item(readline.get_current_history_length() - 1)
        if self.n is None:
            self.n = readline.get_current_history_length() - 1
        command = readline.get_history_item(self.n + 1)  # 1-based
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
        # Make sure that each new line after the first is preceded by a continuation string.
        continued_correctly = []
        correct_termination = self.env().reader.continuation + '\n'
        for line in command_lines[:-1]:
            if not line.endswith(correct_termination):
                assert line[-1] == '\n', line
                line = line[:-1] + correct_termination
            continued_correctly.append(line)
        continued_correctly.append(command_lines[-1])
        self.env().edited_command = ''.join(continued_correctly)
        os.remove(self.tmp_file)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
