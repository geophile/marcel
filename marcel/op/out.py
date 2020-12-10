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
{L,wrap=F}out [-a|--append FILENAME] [-f|--file FILENAME] [-c|--csv] [-p|--pickle] [FORMAT]

{L,indent=4:28}{r:-a}, {r:--append}            Append output to the file identified by FILENAME.

{L,indent=4:28}{r:-f}, {r:--file}              Write output to the file identified by FILENAME, 
replacing an existing file if necessary.

{L,indent=4:28}{r:-c}, {r:--csv}               Format output as comma-separated values.

{L,indent=4:28}{r:-p}, {r:--pickle}            Pickle the output.

{L,indent=4:28}{r:FORMAT}                  The Python formatting specification to be applied to output tuples.


Tuples arriving on the input stream are formatted and written out to a file (or stdout). 

Tuples received on the input stream are passed to the output stream. As a side-effect, input
tuples are formatted and written to stdout or to the specified {r:FILENAME}. 
If the {r:FILENAME} is specified
by {r:--file}, then an existing file is replaced. If the {r:FILENAME} is specified
by {r:--append}, then output is appended to an existing file.

The {r:--append} and {r:--file} options are mutually exclusive.

The formatting options: {r:--csv}, {r:--pickle}, and {r:FORMAT} options are mutually exclusive.
If no formatting options are specified, then the default rendering is used, except
that 1-tuples are unwrapped. (Note that for certain objects, including
{r:File} and {r:Process}, the default rendering is specified by the {n:render_compact()}
or {n:render_full()} methods. Run {n:help object} for more information.)
If the {r:--pickle} formatting option is specified, then output must go to a file, i.e.
{r:--file} or {r:--append} must be specified.

{n:Error} objects are not subject to formatting specifications, and are not passed on as output.
'''


def out(env, append=None, file=None, csv=False, pickle=None, format=None):
    args = []
    if append:
        args.extend(['--append', append])
    if file:
        args.extend(['--file', file])
    if csv:
        args.append('--csv')
    if pickle:
        args.append('--pickle')
    if format:
        args.append(format)
    return Out(env), args


class OutArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('out', env)
        self.add_flag_one_value('append', '-a', '--append', convert=self.check_str, target='append_arg')
        self.add_flag_one_value('file', '-f', '--file', convert=self.check_str, target='file_arg')
        self.add_flag_no_value('csv', '-c', '--csv')
        self.add_flag_no_value('pickle', '-p', '--pickle')
        self.add_anon('format', default=None, convert=self.check_str)
        self.at_most_one('file', 'append')
        self.at_most_one('csv', 'pickle', 'format')
        self.validate()


class Out(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.append_arg = None
        self.append = None
        self.file_arg = None
        self.file = None
        self.csv = False
        self.pickle = False
        self.format = None
        self.output = None
        self.writer = None

    def __repr__(self):
        buffer = []
        if self.file:
            buffer.append(f'file={self.file}')
        if self.append:
            buffer.append(f'append={self.append}')
        if self.csv:
            buffer.append('csv')
        if self.pickle:
            buffer.append('pickle')
        if self.format:
            buffer.append(f'format={Out.ensure_quoted(self.format)}')
        options = ', '.join(buffer)
        return f'out({options})'

    # AbstractOp

    def setup(self):
        self.append = self.eval_function('append_arg', str)
        self.file = self.eval_function('file_arg', str)
        self.format = self.eval_function('format', str)
        if self.append is None and self.file is None and self.pickle:
            raise marcel.exception.KillCommandException(
                'Must specify either --file or --append with --pickle.')
        self.writer = (PythonWriter(self) if self.format else
                       CSVWriter(self) if self.csv else
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
        if op.append or op.file:
            path, mode = (op.append, 'a') if op.append else (op.file, 'w')
            path = os.path.normpath(path)
            path = pathlib.Path(path).expanduser()
            self.output = open(path, mode=mode)
        else:
            self.output = sys.stdout

    def cleanup(self):
        if self.output != sys.stdout:
            self.output.close()

    def write_line(self, x):
        print(x, file=self.output, flush=True)


class CSVWriter(TextWriter):

    def __init__(self, op):
        super().__init__(op)
        self.writer = csv.writer(self,
                                 delimiter=',',
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
        self.writer = (marcel.picklefile.PickleFile(op.append).writer(True)
                       if op.append else
                       marcel.picklefile.PickleFile(op.file).writer(False))

    def receive(self, x):
        self.writer.write(x)

    def cleanup(self):
        self.writer.close()
