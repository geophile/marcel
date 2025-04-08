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
import subprocess
import tempfile

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.main
import marcel.object.workspace
import marcel.runeditor
import marcel.util


HELP = '''
{L,wrap=F}edit [-s|--startup [WORKSPACE]] [COMMAND] 

{L,indent=4:28}{r:-s}, {r:--startup}           Edit the marcel startup script. 
If {r:WORKSPACE} is specified, edit that workspace's startup script, otherwise that of
the current workspace.

{L,indent=4:28}{r:COMMAND}                 The number of the command to be edited.

If no arguments are specified, then the most recently executed command will be edited,
in the editor identified by the {n:EDITOR} environment variable. On exiting the editor, the 
edited command will be on the command line. (Hit enter to run the command, as usual).

If an integer {r:COMMAND} is specified, then the selected command in the command history
will be edited, and then placed on the command line.

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
        self.add_flag_optional_value('startup', '-s', '--startup', default=True)
        self.add_anon('n', convert=self.str_to_int, default=None)
        self.at_most_one('startup', 'n')
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
        self.impl = (EditStartup(self, editor, None if self.startup is True else self.startup)
                     if self.startup else
                     EditCommand(self, editor))

    def run(self, env):
        self.impl.run(env)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True


class EditImpl(object):

    def __init__(self, op, editor):
        self.op = op
        self.editor = editor

    def run(self, env):
        assert False


class EditCommand(EditImpl):

    def __init__(self, op, editor):
        super().__init__(op, editor)
        _, self.tmp_file = tempfile.mkstemp(text=True)

    def run(self, env):
        command = env.reader.command_by_id(self.op.n)
        env.next_command = marcel.runeditor.edit_text(env, command)


class EditStartup(EditImpl):

    def __init__(self, op, editor, ws_name):
        super().__init__(op, editor)
        self.ws_name = ws_name

    def run(self, env):
        if self.ws_name is None:
            workspace = env.workspace
        else:
            workspace = marcel.object.workspace.Workspace.named(self.ws_name)
            if not workspace.exists(env):
                raise marcel.exception.KillCommandException(f'Workspace does not exist: {self.ws_name}')
        marcel.runeditor.edit_file(env, env.locations.config_ws_startup(workspace))
