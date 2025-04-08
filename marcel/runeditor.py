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

import marcel.exception
import marcel.util

def find_editor(env):
    editor = env.getvar('EDITOR')
    if editor is None:
        editor = os.getenv('EDITOR')
        if editor is None:
            raise marcel.exception.KillCommandException(
                "Neither the host OS environment, nor marcel's defines EDITOR")
    return editor

def run_editor(env, file):
    editor = find_editor(env)
    edit_command = f'{editor} {file}'
    process = subprocess.Popen(edit_command,
                               shell=True,
                               executable=marcel.util.bash_executable(),
                               universal_newlines=True)
    process.wait()


def edit_text(env, text):
    _, tmp_file = tempfile.mkstemp(text=True)
    with open(tmp_file, 'w') as output:
        output.write(text)
    run_editor(env, tmp_file)
    with open(tmp_file, 'r') as input:
        command_lines = input.readlines()
    edited = '\n'.join(command_lines)
    os.remove(tmp_file)
    return edited

def edit_file(env, filename):
    run_editor(env, filename)