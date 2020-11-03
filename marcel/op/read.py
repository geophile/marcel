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

import marcel.exception
import marcel.object.file
import marcel.op.filenamesop
import marcel.picklefile
import marcel.util

File = marcel.object.file.File


HELP = '''
{L,wrap=F}read [[-01] [-r|--recursive]] [-c|--csv] [-t|--tsv] [-l|--label] [FILENAME ...]

{L,indent=4:28}{r:-0}                      Include only files matching the specified FILENAMEs, (i.e., depth 0).

{L,indent=4:28}{r:-1}                      Include files matching the specified FILENAMEs, and in any directories
among the FILENAMEs, (i.e., depth 1).

{L,indent=4:28}{r:-r}, {r:--recursive}         Include all files contained in the identified FILENAMEs, recursively,
to any depth.

{L,indent=4:28}{r:-c}, {r:--csv}               Parse CSV-formatted lines with comma separator.

{L,indent=4:28}{r:-t}, {r:--tsv}               Parse CSV-formatted lines with tab separator.

{L,indent=4:28}{r:-p}, {r:--pickle}            Parse pickle format

{L,indent=4:28}{r:-l}, {r:--label}             Include the input {n:File} in the output.

{L,indent=4:28}{r:FILENAME}                A filename or glob pattern.

Reads the contents of the specified files. Input files can be specified on
the command line, (the {r:FILENAME} arguments), or piped in from an upstream command,
typically {r:ls}. In the latter case, input tuples are assumed to be 1-tuples containing {n:File}s. 

Each file is read, and each
line is written to the output stream, with end-of-line characters ({r:\\\\r}, {r:\\\\n}) removed.

If {r:--csv} is specified, then input lines are assumed to be in the CSV format, using a comma
separator. The line is
parsed, and a tuple of fields is output. Similarly, if {r:--tsv} is specified, input
lines are assumed to be in the CSV format with a tab separator.

If {r:--label} is specified, then the input {n:File} is included in the output, in the first
position of each output tuple.
'''


def read(env, *paths, depth=None, recursive=False, csv=False, tsv=False, pickle=False, label=False):
    args = []
    if depth == 0:
        args.append('-0')
    elif depth == 1:
        args.append('-1')
    if recursive:
        args.append('--recursive')
    if csv:
        args.append('--csv')
    if tsv:
        args.append('--tsv')
    if pickle:
        args.append('--pickle')
    if label:
        args.append('--label')
    args.extend(paths)
    return Read(env), args


class ReadArgsParser(marcel.op.filenamesop.FilenamesOpArgsParser):

    def __init__(self, env):
        super().__init__('read', env)
        self.add_flag_no_value('csv', '-c', '--csv')
        self.add_flag_no_value('tsv', '-t', '--tsv')
        self.add_flag_no_value('pickle', '-p', '--pickle')
        self.add_flag_no_value('label', '-l', '--label')
        self.at_most_one('csv', 'tsv', 'pickle')
        self.validate()


class Read(marcel.op.filenamesop.FilenamesOp):

    def __init__(self, env):
        super().__init__(env, Read.read_file)
        self.csv = None
        self.tsv = None
        self.pickle = None
        self.label = None
        self.reader = None

    def __repr__(self):
        depth = ('0' if self.d0 else
                 '1' if self.d1 else
                 'recursive')
        options = [f'depth={depth}']
        if self.label:
            options.append(f'label={self.label}')
        if self.csv:
            options.append('csv')
        if self.tsv:
            options.append('tsv')
        if self.pickle:
            options.append('pickle')
        filenames = [str(p) for p in self.filenames] if self.filenames else '?'
        return f'read({",".join(options)}, filename={filenames})'

    # AbstractOp

    def setup(self):
        self.file = True
        super().setup()
        self.reader = (CSVReader(self) if self.csv or self.tsv else
                       PickleReader(self) if self.pickle else
                       TextReader(self))

    # Op

    def receive(self, x):
        if x is None:
            super().receive(None)
        else:
            if len(x) != 1:
                self.fatal_error(x, 'Input to read must be a single value.')
            file = x[0]
            if type(file) is not File:
                self.fatal_error(x, 'Input to read must be a File.')
            Read.read_file(self, file)

    # FilenamesOp

    @staticmethod
    def read_file(op, file):
        assert type(file) is File, f'{type(file)} {file}'
        if file.is_file():
            op.reader.read_file(op, file, (file,) if op.label else None)


class Reader:
    
    def __init__(self, op):
        self.op = op
        
    def read_file(self, op, file, label):
        assert False


class TextReader(Reader):

    def __init__(self, op):
        super().__init__(op)

    def read_file(self, op, file, label):
        with open(file.path, 'r') as input:
            try:
                line = input.readline()
                while len(line) > 0:
                    line = line.rstrip('\r\n')
                    op.send(label + (line,) if label else line)
                    line = input.readline()
            except StopIteration:
                pass


class PickleReader(Reader):

    def __init__(self, op):
        super().__init__(op)

    def read_file(self, op, file, label):
        with marcel.picklefile.PickleFile(file.path).reader() as input:
            try:
                while True:
                    x = input.read()
                    op.send((label, x) if label else x)
            except EOFError:
                pass


class CSVReader(Reader):
    
    def __init__(self, op):
        super().__init__(op)
        self.input = InputIterator(self)
        self.reader = csv.reader(self.input, delimiter=(',' if op.csv else '\t'))

    def read_file(self, op, file, label):
        with open(file.path, 'r') as input:
            try:
                line = input.readline()
                while len(line) > 0:
                    line = line.rstrip('\r\n')
                    self.input.set_current(line)
                    out = next(self.reader)
                    op.send(label + tuple(out) if label else out)
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

    def set_current(self, x):
        self.current = x
