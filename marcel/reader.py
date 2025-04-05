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

import marcel.tabcompleter


class Reader(object):

    def __init__(self, env):
        self.env = env
        history_file = env.locations.data_ws_hist(env.workspace)
        key_bindings = Reader.setup_key_bindings()
        self.session = prompt_toolkit.PromptSession(
            complete_while_typing=False,
            completer=marcel.tabcompleter.TabCompleter(env),
            history=prompt_toolkit.history.FileHistory(history_file),
            multiline=True,
            key_bindings=key_bindings)

    # Returns a command input by the user.
    def input(self):
        return self.session.prompt(prompt_toolkit.ANSI(self.env.prompt()))

    def take_edited_command(self):
        edited_command = self.env.edited_command
        self.env.edited_command = None
        return edited_command

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