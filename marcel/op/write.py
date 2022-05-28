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
import os.path
import pathlib
import sys

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.error
import marcel.object.renderable
import marcel.picklefile

Renderable = marcel.object.renderable.Renderable

HELP = '''
{L,wrap=F}write [-c|--csv] [-t|--tsv] [-p|--pickle] [-f|--format FORMAT] [-a|--append] [FILENAME]

{L,indent=4:28}{r:-c}, {r:--csv}               Format output as comma-separated values.

{L,indent=4:28}{r:-t}, {r:--tsv}               Format output as tab-separated values.

{L,indent=4:28}{r:-p}, {r:--pickle}            Pickle the output.

{L,indent=4:28}{r:-f}, {r:--format}            Format output according to the Python formatting 
specification {r:FORMAT}.

{L,indent=4:28}{r:-a}, {r:--append}            Append output to the file identified by {r:FILENAME}. 

{L,indent=4:28}FILENAME                Write output to the file identified by {r:FILENAME}. If omitted,
output is written to stdout.

Tuples arriving on the input stream are formatted and written out to a file (or stdout). 

Tuples received on the input stream are passed to the output stream. As a side-effect, input
tuples are formatted and written to stdout or to the specified {r:FILENAME}.
If {r:FILENAME} already exists, its contents will be replaced, unless {r:--append} is specified,
in which case the stream will be appended. {r:--append} is not permitted for writing to stdout.
 
The formatting options {r:--csv}, {r:-tsv} {r:--pickle}, and {r:FORMAT} options are mutually exclusive.
If no formatting options are specified, then the default rendering is used, except
that 1-tuples are unwrapped. (Note that for certain objects, including
{r:File} and {r:Process}, the default rendering is specified by the {n:render_compact()}
or {n:render_full()} methods. Run {n:help object} for more information.)
The {r:--pickle} option is not permitted for writing to stdout.

{n:Error} objects are not subject to formatting specifications, and are not passed on as output.
'''

COMMA = ','
TAB = '\t'


def write(env, filename=None, csv=False, tsv=False, pickle=False, format=None, append=False):
    args = []
    if csv:
        args.append('--csv')
    if tsv:
        args.append('--tsv')
    if pickle:
        args.append('--pickle')
    if format:
        args.extend(['--format', format])
    if append:
        args.append('--append')
    if filename:
        args.append(filename)
    return Write(env), args


class WriteArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('write', env)
        self.add_flag_no_value('csv', '-c', '--csv')
        self.add_flag_no_value('tsv', '-t', '--tsv')
        self.add_flag_no_value('pickle', '-p', '--pickle')
        self.add_flag_one_value('format', '-f', '--format')
        self.add_flag_no_value('append', '-a', '--append')
        self.add_anon('filename', convert=self.check_str, default=None, target='filename_arg')
        self.at_most_one('csv', 'tsv', 'pickle', 'format')
        self.validate()


class Write(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.csv = False
        self.tsv = False
        self.pickle = False
        self.format = None
        self.append = None
        self.filename_arg = None
        self.filename = None
        self.output = None
        self.writer = None

    def __repr__(self):
        buffer = []
        if self.csv:
            buffer.append('csv')
        if self.tsv:
            buffer.append('tsv')
        if self.pickle:
            buffer.append('pickle')
        if self.format:
            buffer.append(f'format={Write.ensure_quoted(self.format)}')
        if self.append:
            buffer.append('append')
        if self.filename_arg:
            buffer.append(f'file={self.filename_arg}')
        options = ', '.join(buffer)
        return f'write({options})'

    # AbstractOp

    def setup(self):
        self.filename = self.eval_function('filename_arg', str)
        if self.pickle and self.filename is None:
            raise marcel.exception.KillCommandException(
                '--pickle incompatible with stdout.')
        if self.append and self.filename is None:
            raise marcel.exception.KillCommandException(
                '--append incompatible with stdout.')
        self.writer = (PythonWriter(self) if self.format else
                       CSVWriter(self, COMMA) if self.csv else
                       CSVWriter(self, TAB) if self.tsv else
                       PickleWriter(self) if self.pickle else
                       DefaultWriter(self))

    def receive(self, x):
        try:
            self.writer.receive(x)
        except marcel.exception.KillAndResumeException as e:
            self.non_fatal_error(input=x, message=str(e))
        except Exception as e:  # E.g. UnicodeEncodeError
            self.non_fatal_error(input=x, message=str(e))
        finally:
            self.send(x)

    def cleanup(self):
        self.writer.cleanup()

    # For use by this class

    @staticmethod
    def ensure_quoted(x):
        if x is None:
            return 'None'
        elif type(x) in (int, float):
            return str(x)
        elif isinstance(x, str):
            if "'" not in x:
                return "'{}'".format(x)
            elif '"' not in x:
                return '"{}"'.format(x)
            else:
                return "'{}'".format(x.replace("'", "\\'"))
        else:
            return str(x)


class Writer:

    def __init__(self, op):
        self.op = op

    def receive(self, x):
        assert False

    def cleanup(self):
        pass


class TextWriter(Writer):

    def __init__(self, op):
        super().__init__(op)
        if op.filename:
            path = pathlib.Path(os.path.normpath(op.filename)).expanduser()
            self.output = open(path, mode='a' if op.append else 'w')
        else:
            self.output = sys.stdout

    def cleanup(self):
        if self.output != sys.stdout:
            self.output.close()

    def write_line(self, x):
        print(x, file=self.output, flush=True)


class CSVWriter(TextWriter):

    def __init__(self, op, delimiter):
        super().__init__(op)
        self.writer = csv.writer(self,
                                 delimiter=delimiter,
                                 quotechar="'",
                                 quoting=csv.QUOTE_MINIMAL,
                                 lineterminator='')
        self.row = None

    def receive(self, x):
        self.writer.writerow(x)
        self.write_line(self.row)

    def write(self, x):
        self.row = x


class PythonWriter(TextWriter):

    def __init__(self, op):
        super().__init__(op)
        self.format = op.format

    def receive(self, x):
        self.write_line(self.format.format(*x))


class DefaultWriter(TextWriter):

    def __init__(self, op):
        super().__init__(op)
        self.color_scheme = (op.env().color_scheme()
                             if self.output == sys.__stdout__ else
                             None)

    def receive(self, x):
        t = type(x)
        if t in (list, tuple):
            if len(x) == 1:
                out = x[0]
                if isinstance(out, Renderable):
                    out = out.render_full(self.color_scheme)
            else:
                out = str(x)
        elif x is None:
            out = None
        else:
            assert False, type(x)
        self.write_line(out)


class PickleWriter(Writer):

    def __init__(self, op):
        super().__init__(op)
        assert op.filename is not None  # Should have been checked in setup
        self.writer = marcel.picklefile.PickleFile(op.filename).writer(op.append)

    def receive(self, x):
        self.writer.write(x)

    def cleanup(self):
        self.writer.close()
