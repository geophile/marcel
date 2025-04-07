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

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.historyrecord


HELP = '''
{L,wrap=F}history [-c|--command STRING] [-a|--all] [N]

{L,indent=4:28}{r:-c}, {r:--command}           Report only the commands containing the specified STRING.

{L,indent=4:28}{r:N}                       Include the last N qualifying items.

Generates a stream containing the history of commands executed, in chronological order (newest last).
The number identifying each command can be used in conjunction with the {r:edit}, {r:run}, 
and {r:!} operators.

If {r:--command} is specified, then only the commands containing the specified {r:STRING} will be
selected. 

If {r:--all} is specified, then all qualifying commands will be output.

If {r:N} is provided, it must be a positive integer. The most recent {r:N} qualifying commands will be output.
(I.e., If {r:--command} is specified, than that filter is applied first, and then the last {r:N} items
are selected.)

If neither {r:N} nor {r:--all} are specified, then the last 20 qualifying commands will be output. 
{r:N} and {r:--all} are mutually exclusive.
'''


def history():
    return History()


class HistoryArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('history', env)
        self.add_flag_one_value('pattern', '-c', '--command')
        self.add_flag_no_value('all', '-a', '--all')
        self.add_anon('n', convert=self.str_to_int, default=None)
        self.at_most_one('all', 'n')
        self.validate()


class History(marcel.core.Op):

    N_DEFAULT = 20

    def __init__(self):
        super().__init__()
        self.pattern = None
        self.all = None
        self.n = None

    def __repr__(self):
        args = []
        if self.pattern:
            args.append(f"command='{self.pattern}'")
        if self.all:
            args.append('all')
        if self.n is not None:
            args.append(f'n={self.n}')
        args_description = ', '.join(args)
        return f'history({args_description})'

    # AbstractOp

    def setup(self, env):
        self.n = self.eval_function(env, 'n', int)
        if not self.all and self.n is None:
            self.n = History.N_DEFAULT
        if self.n is not None and self.n < 1:
            raise marcel.exception.KillCommandException('n must be a posiive integer')
        assert (not self.all and type(self.n) is int) or (self.all and self.n is None), self

    def run(self, env):
        history = env.reader.history()
        selected = []
        n_history = len(history)
        for i in range(n_history):  # History is newest-to-oldest
            command = history[i]
            if self.pattern is None or self.pattern in command:
                selected.append(marcel.object.historyrecord.HistoryRecord(n_history - 1 - i, command))
                if len(selected) == self.n:
                    break
        selected.reverse()
        for history_record in selected:
                self.send(env, history_record)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
