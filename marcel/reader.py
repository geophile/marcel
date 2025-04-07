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

import marcel.exception
import marcel.tabcompleter


class Reader(object):

    def __init__(self, env):
        self._env = env
        history_file = env.locations.data_ws_hist(env.workspace)
        key_bindings = Reader.setup_key_bindings()
        self._history = prompt_toolkit.history.FileHistory(history_file)
        self._command_history = []
        self._selected_command_id = None
        self._session = prompt_toolkit.PromptSession(
            complete_while_typing=False,
            completer=marcel.tabcompleter.TabCompleter(env),
            history=self._history,
            multiline=True,
            key_bindings=key_bindings)

    # Returns a command input by the user.
    def input(self):
        return self._session.prompt(prompt_toolkit.ANSI(self._env.prompt()))

    # Returns list of commands, newest-to-oldest.
    def history(self):
        history = list(self._history.load_history_strings())
        if len(self._command_history) < len(history):
            self._command_history = history
        return self._command_history

    def select_command_by_id(self, id):
        self._selected_command_id = id

    def take_selected_command(self):
        selected_command = None
        id = self._selected_command_id
        if id is not None:
            history = self.history()
            if type(id) is not int or id < 0:
                raise marcel.exception.KillCommandException(
                    f'Command id must be a non-negative integer: {id}')
            if id >= len(history):
                raise marcel.exception.KillCommandException(
                    f'Command id exceeds that of most recent command: {id} > {len(history) - 1}')
            selected_command =  self.history()[len(history) - 1 - id]
            self._selected_command_id = None
        return selected_command

    # Set up key bindings:
    # - Enter terminates the text of a command.
    # - Alt-Enter terminates a line of text but continues the command.
    @staticmethod
    def setup_key_bindings():
        kb = prompt_toolkit.key_binding.KeyBindings()

        @kb.add('escape', 'enter')
        def _(event):
            event.current_buffer.insert_text('\n')

        @kb.add('enter')
        def _(event):
            event.current_buffer.validate_and_handle()

        return kb