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
{L,wrap=F}history [-c|--command STRING] [N]

{L,indent=4:28}{r:-c}, {r:--command}           Report only the commands containing the specified STRING.

{L,indent=4:28}{r:N}                       Include the last N qualifying items.

Generates a stream containing the history of commands executed, in chronological order (newest last).
The number identifying each command can be used in conjunction with the {r:edit}, {r:run}, 
and {r:!} operators.

If {r:--command} is specified, then only the commands containing the specified {r:STRING} will be
selected. 

If {r:N} is provided, it must be a positive integer. The most recent {r:N} qualifying commands will be output.
(I.e., If {r:--command} is specified, than that filter is applied first, and then the last {r:N} items
are selected.)
'''


def history(env):
    return History(env)


class HistoryArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('history', env)
        self.add_flag_one_value('command', '-c', '--command')
        self.add_anon('n', convert=self.str_to_int, default=None)
        self.validate()


class History(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.command = None
        self.n = None

    def __repr__(self):
        args = []
        if self.command:
            args.append(f"command='{self.command}'")
        if self.n is not None:
            args.append(f'n={self.n}')
        args_description = '\n'.join(args)
        return f'history({args_description})'

    # AbstractOp

    def run(self):
        history = self.env().reader.history()
        selected = []
        for i in range(len(history)):
            if self.command is None or self.command in history[i]:
                selected.append(marcel.object.historyrecord.HistoryRecord(i, history[i]))
        output = (selected
                  if self.n is None else
                  selected[-self.n:])
        for record in output:
            self.send(record)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
