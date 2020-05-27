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

import readline

import marcel.argsparser
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


def run(env):
    return Run(env)


class RunArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('run', env)
        self.add_anon('n', convert=self.str_to_int, default=None)
        self.validate()


class Run(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.expected_args = None  # Set during parse. ! -> 1, !! -> 0
        self.n = None
        self.editor = None
        self.tmp_file = None

    def __repr__(self):
        return 'run()' if self.n is None else f'run({self.n})'

    # BaseOp

    def setup_1(self):
        if self.expected_args == 1 and self.n is None:
            raise marcel.exception.KillCommandException('History command number required following !')
        elif self.expected_args == 0 and self.n is not None:
            raise marcel.exception.KillCommandException('No arguments permitted after !!')

    def receive(self, _):
        # Remove the run command from history
        readline.remove_history_item(readline.get_current_history_length() - 1)
        if self.n is None:
            self.n = readline.get_current_history_length() - 1
        self.env().edited_command = readline.get_history_item(self.n + 1)  # 1-based

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
