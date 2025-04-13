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

import prompt_toolkit
import prompt_toolkit.history
import prompt_toolkit.key_binding
from prompt_toolkit.shortcuts import CompleteStyle

import marcel.exception
import marcel.runeditor
import marcel.tabcompleter


class Reader(object):

    def __init__(self, env):
        self._env = env
        self._history = prompt_toolkit.history.FileHistory(env.locations.data_ws_hist(env.workspace))
        self._command_history = []
        self._selected_command_id = None
        self._session = prompt_toolkit.PromptSession(
            complete_while_typing=False,
            complete_style=CompleteStyle.MULTI_COLUMN,
            completer=marcel.tabcompleter.TabCompleter(env),
            history=self._history,
            multiline=True,
            key_bindings=self.setup_key_bindings(),
            enable_open_in_editor=True)

    # Returns a command input by the user.
    def input(self):
        return self._session.prompt(prompt_toolkit.ANSI(self._env.prompt()))

    # Returns list of commands, newest-to-oldest.
    def history(self):
        history = list(self._history.load_history_strings())
        if len(self._command_history) < len(history):
            self._command_history = history
        return self._command_history

    def command_by_id(self, id):
        history = self.history()
        if type(id) is not int or id < 0:
            raise marcel.exception.KillCommandException(
                f'Command id must be a non-negative integer: {id}')
        if id >= len(history):
            raise marcel.exception.KillCommandException(
                f'Command id exceeds that of most recent command: {id} > {len(history) - 1}')
        return self.history()[len(history) - 1 - id]

    # Handle !, !!, and edit ops. For edit, only edit N is handled here. edit -s is left to normal
    # command processing.
    def handle_edit_and_run(self, command):
        def parse(command):
            command = command.strip()
            return (['!!'] + command[2:].split() if command.startswith('!!') else
                    ['!'] + command[1:].split() if command.startswith('!') else
                    ['edit'] + command[4:].split() if command.startswith('edit') else
                    None)

        def selected_command(token):
            assert token is not None
            try:
                command_id = int(token)
                return self.command_by_id(command_id)
            except ValueError:
                raise marcel.exception.KillCommandException(f'Command must be identifed by an integer: {t1}')

        new_command = None
        tokens = parse(command)
        if tokens is not None:
            t0 = tokens[0]
            t1 = tokens[1] if len(tokens) > 1 else None
            if t0 == '!':
                if len(tokens) == 0:
                    raise marcel.exception.KillCommandException('History command number required following !')
                elif len(tokens) > 2:
                    raise marcel.exception.KillCommandException('Too many arguments after !')
                new_command = selected_command(t1)
            elif t0 == '!!':
                if len(tokens) > 1:
                    raise marcel.exception.KillCommandException('No arguments permitted after !!')
                command_id = len(self.history()) - 1
                new_command = self.command_by_id(command_id)
            elif t0 == 'edit':
                if t1 is None:
                    raise marcel.exception.KillCommandException('Missing command number')
                elif t1 in ('-s', '--startup'):
                    # Return None, which will leave the command as is. Normal command processing should then
                    # operate, editing the selected workspace's startup script.
                    pass
                else:
                    command = selected_command(t1)
                    new_command = marcel.runeditor.edit_text(self._env, command)
        return new_command


    # Set up key bindings:
    # - Enter terminates the text of a command.
    # - Alt-Enter terminates a line of text but continues the command.
    def setup_key_bindings(self):
        kb = prompt_toolkit.key_binding.KeyBindings()

        @kb.add('escape', 'enter')
        def _(event):
            event.current_buffer.insert_text('\n')

        @kb.add('enter')
        def _(event):
            buffer = event.current_buffer
            replacement = self.handle_edit_and_run(buffer.document.text)
            if replacement:
                original = buffer.document.text
                buffer.delete_before_cursor(len(original))
                buffer.insert_text(replacement)
            buffer.validate_and_handle()

        return kb