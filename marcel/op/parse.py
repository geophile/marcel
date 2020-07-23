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

import csv

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.util


HELP = '''
{L,wrap=F}parse -c|--csv [-t|--tab]

{L,indent=4:28}{r:-c}, {r:--csv}               Parse CSV-formatted data

{L,indent=4:28}{r:-t}, {r:--tab}               CSV delimiter is a tab.

Parse incoming data and generate output containing structured data. Currently,
the only recognized format is CSV.

Input presumably consists of 1-tuples containing data in CSV format. Each input
row is parsed, and an output tuple is generated, with each field as
one element of the tuple.

The field delimiter is a comma by default, a tab if {r:--tab} is specified.
'''


def parse(env, csv=False, tab=False):
    args = []
    if csv:
        args.append('--csv')
    if tab:
        args.append('--tab')
    return Parse(env), args


class ParseArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('parse', env)
        self.add_flag_no_value('csv', '-c', '--csv')
        self.add_flag_no_value('tab', '-t', '--tab')
        self.validate()


class Parse(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.csv = None
        self.csv_input = None
        self.csv_reader = None
        self.tab = None

    # AbstractOp

    def setup_1(self):
        if self.csv is None:
            raise marcel.exception.KillCommandException('Format not specified, (currently only -c|--csv).')
        self.csv_input = InputIterator(self)
        self.csv_reader = csv.reader(self.csv_input, delimiter='\t' if self.tab else ',')

    def receive(self, x):
        if len(x) != 1:
            self.fatal_error(x, 'Input to parse must be a single value.')
        self.csv_input.set(x[0])
        try:
            self.send(next(self.csv_reader))
        except StopIteration:
            pass


class InputIterator:

    def __init__(self, op):
        self.op = op
        self.current = None

    def __iter__(self):
        return self

    def __next__(self):
        if self.current:
            next = self.current
            self.current = None
            return next
        else:
            raise StopIteration()

    def set(self, x):
        self.current = x
