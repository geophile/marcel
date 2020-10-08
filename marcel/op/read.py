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
import marcel.object.file
import marcel.util

File = marcel.object.file.File


HELP = '''
{L,wrap=F}read [-c|--csv] [-t|--tsv] [-l|--label]

{L,indent=4:28}{r:-c}, {r:--csv}               Parse CSV-formatted lines with comma separator.

{L,indent=4:28}{r:-t}, {r:--tsv}               Parse CSV-formatted lines with tab separator.

{L,indent=4:28}{r:-l}, {r:--label}             Include the input {n:File} in the output.

Input tuples are assumed to be 1-tuples containing {n:File}s. Each file is read, and each
line is written to the output stream, with end-of-line characters ({r:\\\\r}, {r:\\\\n}) removed.

If {r:--csv} is specified, then input lines are assumed to be in the CSV format, using a comma
separator. The line is
parsed, and a tuple of fields is output. Similarly, if {r:--tsv} is specified, input
lines are assumed to be in the CSV format with a tab separator.

If {r:--label} is specified, then the input {n:File} is included in the output, in the first
position of the output tuple. 
'''


def read(env, csv=False, tsv=False, label=False):
    args = []
    if csv:
        args.append('--csv')
    if tsv:
        args.append('--tsv')
    if label:
        args.append('--label')
    return Read(env), args


class ReadArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('parse', env)
        self.add_flag_no_value('csv', '-c', '--csv')
        self.add_flag_no_value('tsv', '-t', '--tsv')
        self.add_flag_no_value('label', '-l', '--label')
        self.at_most_one('csv', 'tsv')
        self.validate()


class Read(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.csv = None
        self.tsv = None
        self.label = None
        self.csv_input = None
        self.csv_reader = None
        self.file = None

    def __repr__(self):
        options = []
        if self.label:
            options.append(f'label={self.label}')
        if self.csv:
            options.append('csv')
        if self.tsv:
            options.append('tsv')
        return f'read({",".join(options)})'

    # AbstractOp

    def setup_1(self):
        if self.csv or self.tsv:
            self.csv_input = InputIterator(self)
            self.csv_reader = csv.reader(self.csv_input, delimiter=(',' if self.csv else '\t'))

    def receive(self, x):
        if len(x) != 1:
            self.fatal_error(x, 'Input to read must be a single value.')
        file = x[0]
        if type(file) is not File:
            self.fatal_error(x, 'Input to read must be a File.')
        label = [file] if self.label else None
        with open(file.path, 'r') as input:
            try:
                if self.csv_reader:
                    line = input.readline()
                    while len(line) > 0:
                        line = line.rstrip('\r\n')
                        self.csv_input.set(line)
                        out = next(self.csv_reader)
                        self.send(label + out if label else out)
                        line = input.readline()
                else:
                    line = input.readline()
                    while len(line) > 0:
                        line = line.rstrip('\r\n')
                        self.send(label + [line] if label else line)
                        line = input.readline()
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
