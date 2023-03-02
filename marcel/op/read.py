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

from collections import namedtuple
import csv

import marcel.exception
import marcel.object.file
import marcel.op.filenamesop
import marcel.picklefile
import marcel.util

File = marcel.object.file.File

HELP = '''
{L,wrap=F}read [[-01] [-r|--recursive]] [-c|--csv] [-t|--tsv] [-h|--headings] [-s|--skip-headings] [-p|--pickle] [-l|--label] [FILENAME ...]

{L,indent=4:28}{r:-0}                      Include only files matching the specified FILENAMEs, (i.e., depth 0).

{L,indent=4:28}{r:-1}                      Include files matching the specified FILENAMEs, and in any directories
among the FILENAMEs, (i.e., depth 1).

{L,indent=4:28}{r:-r}, {r:--recursive}         Include all files contained in the identified FILENAMEs, recursively,
to any depth.

{L,indent=4:28}{r:-c}, {r:--csv}               Parse CSV-formatted lines with comma delimiter.

{L,indent=4:28}{r:-t}, {r:--tsv}               Parse CSV-formatted lines with tab delimiter.

{L,indent=4:28}{r:-h}, {r:--headings}          First line of CSV or TSV file contains column headings.

{L,indent=4:28}{r:-s}, {r:--skip-headings}     Skip first line of CSV or TSV file, which presumably contains headings.

{L,indent=4:28}{r:-p}, {r:--pickle}            Parse pickle format

{L,indent=4:28}{r:-l}, {r:--label}             Include the input {n:File} with output tuple.

{L,indent=4:28}{r:FILENAME}                A filename or glob pattern.

Reads the contents of the specified files. Input files can be specified on
the command line, by giving their names (the {r:FILENAME} arguments); or piped in from an upstream command,
typically {r:ls}. In the latter case, input tuples are assumed to be 1-tuples containing {n:File}s. 

Each file is read, and each
line is written to the output stream, with end-of-line characters ({r:\\\\r}, {r:\\\\n}) removed.

If {r:--csv} is specified, then input lines are assumed to be in the CSV format, using a comma
delimiter. The line is
parsed, and a tuple of fields is output. Similarly, if {r:--tsv} is specified, input
lines are assumed to be in the CSV format with a tab delimiter.

{r:--headings} can only be used in conjunction with {r:--csv} or {r:--tsv}. It indicates that
the first line of input is a set of column headings, and that these headings should be used to
identify columns through the use of named tuples. If a column heading
is not a valid Python identifier, an attempt will be made to generate a Python identifier,
replacing invalid characters by {r:_}. If one of the lines of the input has fewer fields
than there are headings, the corresponding tuple will be padded with None. If an input line has more
fields than there are headings, an {r:Error} is generated.

{r:-s|--skip-headings} can only be used in conjunction with {r:--csv} or {r:--tsv}. 
This option causes the first line of the file to be skipped, presumably because it contains headings
which are not of interest.  

If {r:--pickle} is specified, the input is assumed to be in pickle format.
If none of these are specified, then each input is assumed to be a line of text. End-of-line
characters are removed.

If {r:--label} is specified, then the input {n:File} is included in the output, in the first
position of each output tuple. If {r:--headings} is specified, then the label column will be named
{r:LABEL}.
'''

COMMA = ','
TAB = '\t'


def read(env, *filenames,
         depth=None,
         recursive=False,
         csv=False,
         tsv=False,
         headings=False,
         skip_headings=False,
         pickle=False,
         label=False):
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
    if headings:
        args.append('--headings')
    if skip_headings:
        args.append('--skip-headings')
    if pickle:
        args.append('--pickle')
    if label:
        args.append('--label')
    args.extend(filenames)
    return Read(env), args


class ReadArgsParser(marcel.op.filenamesop.FilenamesOpArgsParser):

    def __init__(self, env):
        super().__init__('read', env)
        self.add_flag_no_value('csv', '-c', '--csv')
        self.add_flag_no_value('tsv', '-t', '--tsv')
        self.add_flag_no_value('headings', '-h', '--headings')
        self.add_flag_no_value('skip_headings', '-s', '--skip-headings')
        self.add_flag_no_value('pickle', '-p', '--pickle')
        self.add_flag_no_value('label', '-l', '--label')
        self.at_most_one('csv', 'tsv', 'pickle')
        self.at_most_one('headings', 'skip_headings')
        self.validate()


class Read(marcel.op.filenamesop.FilenamesOp):

    def __init__(self, env):
        super().__init__(env, Read.read_file)
        self.csv = None
        self.tsv = None
        self.headings = None
        self.skip_headings = None
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
        if self.headings:
            options.append('headings')
        if self.pickle:
            options.append('pickle')
        if self.filenames:
            filenames = [str(p) for p in self.filenames]
            return f'read({",".join(options)}, filenames={filenames})'
        else:
            return f'read({",".join(options)})'

    # AbstractOp

    def setup(self):
        if self.headings and not (self.csv or self.tsv):
            raise marcel.exception.KillCommandException(
                '-h|--headings can only be specified with -c|--csv or -t|--tsv')
        if self.skip_headings and not (self.csv or self.tsv):
            raise marcel.exception.KillCommandException(
                '-s|--skip-headings can only be specified with -c|--csv or -t|--tsv')
        self.file = True
        super().setup()
        self.reader = (CSVReader(self, COMMA) if self.csv else
                       CSVReader(self, TAB) if self.tsv else
                       PickleReader(self) if self.pickle else
                       TextReader(self))

    # Op

    def run(self):
        if self.filenames:
            return super().run()
        else:
            return self.receive(None)

    def receive(self, x):
        if x is None:
            super().receive(None)
        else:
            if len(x) != 1:
                self.fatal_error(x, 'Input to read must be a single value.')
            file = x[0]
            if type(file) is not File:
                self.fatal_error(x, 'Input to read must be a File.')
            self.read_file(file)

    # Internal

    def read_file(self, file):
        assert type(file) is File, f'{type(file)} {file}'
        if file.is_file():
            self.reader.read_file(file, (file,) if self.label else None)


class Reader:

    def __init__(self, op):
        self.op = op

    def read_file(self, file, label):
        assert False


class TextReader(Reader):

    def __init__(self, op):
        super().__init__(op)

    def read_file(self, file, label):
        with open(file.path, 'r') as input:
            try:
                line = input.readline()
                while len(line) > 0:
                    line = line.rstrip('\r\n')
                    self.op.send(label + (line,) if label else line)
                    line = input.readline()
            except StopIteration:
                pass


class PickleReader(Reader):

    def __init__(self, op):
        super().__init__(op)

    def read_file(self, file, label):
        with marcel.picklefile.PickleFile(file.path).reader() as input:
            try:
                while True:
                    x = input.read()
                    self.op.send((label, x) if label else x)
            except EOFError:
                pass


class CSVReader(Reader):
    IDENTIFIER_CHARS = '_0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def __init__(self, op, delimiter):
        super().__init__(op)
        self.input = InputIterator(self)
        self.reader = csv.reader(self.input, delimiter=delimiter)
        self.headings = op.headings
        self.skip_headings = op.skip_headings
        # For --headings
        self.named_tuple = None
        self.n_columns = None

    def read_file(self, file, label):
        with open(file.path, 'r') as input:
            try:
                first = True
                line = input.readline()
                while len(line) > 0:
                    line = line.rstrip('\r\n')
                    self.input.set_current(line)
                    out = tuple(next(self.reader))
                    if first and (self.headings or self.skip_headings):
                        if self.headings:
                            try:
                                headings = self.extract_headings(out)
                                self.named_tuple = namedtuple('csvtuple', headings)
                                self.n_columns = len(headings)
                            except ValueError as e:
                                self.op.non_fatal_error(line,
                                                        f'Cannot generate identifiers from headings: {e}')
                    else:
                        if label:
                            out = label + tuple(out)
                        if self.named_tuple:
                            try:
                                if len(out) < self.n_columns:
                                    out = out + ((None,) * (self.n_columns - len(out)))
                                out = self.named_tuple(*out)
                            except Exception as e:
                                self.op.non_fatal_error(line,
                                                        'Incompatible with headings, '
                                                        '(probably too many fields).')
                                out = None
                        if out is not None:
                            self.op.send(out)
                    line = input.readline()
                    first = False
            except StopIteration:
                pass

    def extract_headings(self, fields):
        headings = []
        if self.op.label:
            headings.append('LABEL')
        for field in fields:
            field = field.strip()
            if not field.isidentifier():
                for i in range(len(field)):
                    if field[i] not in CSVReader.IDENTIFIER_CHARS:
                        field = field[:i] + '_' + field[i + 1:]
            # field might still be invalid as an identifier, in case it starts with a digit.
            # namedtuple construction will complain if this is the case.
            headings.append(field)
        return headings


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
