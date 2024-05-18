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

import os
import readline
import subprocess
import tempfile

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.main
import marcel.util


HELP = '''
{L,wrap=F}edit [-s|--startup] [COMMAND] 

{L,indent=4:28}{r:-s}, {--startup}           Edit the marcel startup script.

{L,indent=4:28}{r:COMMAND}                 The number of the command to be edited.

Open an editor to edit the command identified by {r:COMMAND} in the command history,
(obtained by running the {n:history} operator). I {r:COMMAND} is omitted, the most recently
executed command will be edited. The editor is selected by the {n:EDITOR}
environment variable. On exiting the editor, the edited command
will be on the command line. (Hit enter to run the command, as usual.)

If {r:--startup} is specified, then the marcel startup script for the current workspace is edited.
'''


def edit(n=None, startup=False):
    args = []
    if n is not None:
        args.append(n)
    if startup:
        args.append(startup)
    return Edit(), [] if n is None else [n]


class EditArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('edit', env)
        self.add_flag_no_value('startup', '-s', '--startup')
        self.add_anon('n', convert=self.str_to_int, default=None)
        self.validate()


class Edit(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.n = None
        self.startup = None
        self.editor = None
        self.impl = None

    def __repr__(self):
        return 'edit()'

    # AbstractOp

    def setup(self, env):
        editor = Edit.find_editor(env)
        self.impl = EditStartup(self, editor) if self.startup else EditCommand(self, editor)

    def run(self, env):
        self.impl.run(env)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True

    # Internal

    @staticmethod
    def find_editor(env):
        editor = env.getvar('EDITOR')
        if editor is None:
            editor = os.getenv('EDITOR')
            if editor is None:
                raise marcel.exception.KillCommandException(
                    "Neither the host OS environment, nor marcel's defines EDITOR")
        return editor


class EditImpl(object):

    def __init__(self, op, editor):
        self.op = op
        self.editor = editor

    def run(self, env):
        assert False

    # For use by subclasses

    def edit(self, file):
        edit_command = f'{self.editor} {file}'
        process = subprocess.Popen(edit_command,
                                   shell=True,
                                   executable=marcel.util.bash_executable(),
                                   universal_newlines=True)
        process.wait()


class EditCommand(EditImpl):

    def __init__(self, op, editor):
        super().__init__(op, editor)
        _, self.tmp_file = tempfile.mkstemp(text=True)

    def run(self, env):
        # Remove the edit command from history
        readline.remove_history_item(readline.get_current_history_length() - 1)
        if self.op.n is None:
            self.op.n = readline.get_current_history_length() - 1
        command = readline.get_history_item(self.op.n + 1)  # 1-based
        assert command is not None
        with open(self.tmp_file, 'w') as output:
            output.write(command)
        self.edit(self.tmp_file)
        with open(self.tmp_file, 'r') as input:
            command_lines = input.readlines()
        # Make sure that each new line after the first is preceded by a continuation string.
        continued_correctly = []
        correct_termination = env.reader.continuation + '\n'
        for line in command_lines[:-1]:
            if not line.endswith(correct_termination):
                assert line[-1] == '\n', line
                line = line[:-1] + correct_termination
            continued_correctly.append(line)
        continued_correctly.append(command_lines[-1])
        env.edited_command = ''.join(continued_correctly)
        os.remove(self.tmp_file)


class EditStartup(EditImpl):

    def run(self, env):
        self.edit(env.locations.config_ws_startup(env.workspace))
