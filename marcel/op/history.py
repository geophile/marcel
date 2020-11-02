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

import marcel.argsparser
import marcel.core
import marcel.object.historyrecord


HELP = '''
{L,wrap=F}history [N]

Generates a stream containing the history of commands executed, in chronological order (newest last).
The number identifying each command can be used in conjunction with the {r:edit}, {r:run}, 
and {r:!} operators.

If {r:N} is provided, it must be a positive integer. The most recent {r:N} commands will be output.
'''


def history(env):
    return History(env)


class HistoryArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('history', env)
        self.add_anon('n', convert=self.str_to_int, default=None)
        self.validate()


class History(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.n = None

    def __repr__(self):
        return 'history()' if self.n is None else f'history({self.n})'

    # AbstractOp

    def receive(self, _):
        history = self.env().reader.history()
        start = 0 if self.n is None else len(history) - self.n
        for i in range(start, len(history)):
            self.send(marcel.object.historyrecord.HistoryRecord(i, history[i]))

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
