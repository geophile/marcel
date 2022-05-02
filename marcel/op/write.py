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
import marcel.reservoir
import marcel.util

Renderable = marcel.object.renderable.Renderable

COMMA = ','
TAB = '\t'

HELP = '''
{L,wrap=F}write [-a|--append] [-c|--csv] [-t|--tsv] [-p|--pickle] [-f|--format FORMAT] [NAME]
{L,wrap=F}write > NAME
{L,wrap=F}write >> NAME

{L,indent=4:28}{r:-a}, {r:--append}            Append output to previous output.

{L,indent=4:28}{r:-c}, {r:--csv}               Format output as comma-separated values.

{L,indent=4:28}{r:-t}, {r:--tsv}               Format output as tab-separated values.

{L,indent=4:28}{r:-p}, {r:--pickle}            Pickle the output.

{L,indent=4:28}{r:-f}, {r:--format}            Format the output using the specification
given by {r:FORMAT}.

{L,indent=4:28}{r:NAME}                    A variable name or filename. Write to stdout.
if omitted.

Tuples received on the input stream are passed to the output stream.
As a side-effect, input tuples are formatted and written to a
variable (which accumulates received tuples in a list), a file, or to stdout.

The output target is:

- A variable, if {r:NAME} is a Python identifier.

- A file, if {r:NAME} begins with ., ~ or /.

- stdout if {r:NAME} is omitted.

If {r:--append} is specified, then the output is appended to previously
written output. (This applies to files and variables. The option is not applicable
to stdout.)

The formatting options ({r:--csv,} {r:--tsv,} {r:--pickle,}
{r:--format)} may only be used if writing to a file or to
stdout. These options are mutually exclusive. 
The {r:--pickle} option is not permitted for writing to stdout.

If writing to a file or stdout, and no formatting option is provided,
then the default rendering is used, except that 1-tuples are
unwrapped. (Note that for certain objects, including File and Process,
the default rendering is specified by the {n:render_compact()} or
{n:render_full()} methods. Run help object for more information.)

{n:Error} objects are not subject to formatting specifications, and are
not passed on as output.

There is special syntax for the {n:write} operator: 

{L,indent=4,wrap=F}... | store NAME

can be written as

{L,indent=4,wrap=F}... > NAME

Similarly, 

{L,indent=4,wrap=F}... | store --append NAME

can be written as 

{L,indent=4,wrap=F}... >> NAME

This syntax is designed to be reminiscent of bash behavior for files,
but it accommodates variables as well.
'''


def write(env, append=False, csv=False, tsv=False, pickle=False, format=None, var=None, file=None):
    args = []
    if append:
        args.extend(['--append', append])
    if csv:
        args.append('--csv')
    if tsv:
        args.append('--tsv')
    if pickle:
        args.append('--pickle')
    if format:
        args.extend(['--format', format])
    if file and var:
        raise marcel.exception.KillCommandException('Cannot specify values for both var and file')
    if var:
        args.append(var)
    if file:
        args.append(file)
    return Write(env), args


class WriteArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('write', env)
        self.add_flag_no_value('append', '-a', '--append')
        self.add_flag_no_value('csv', '-c', '--csv')
        self.add_flag_no_value('tsv', '-t', '--tsv')
        self.add_flag_no_value('pickle', '-p', '--pickle')
        self.add_flag_one_value('format', '-f', '--format', convert=self.check_str)
        self.add_anon('name', default=None, convert=self.check_str_or_file, target="name_arg")
        self.at_most_one('csv', 'tsv', 'pickle', 'format')
        self.validate()


class Write(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.append = None
        self.csv = False
        self.tsv = False
        self.pickle = False
        self.format = None
        self.output = None
        self.name = None
        self.name_arg = None
        self.writer = None

    def __repr__(self):
        buffer = []
        if self.append:
            buffer.append(f'append')
        if self.csv:
            buffer.append('csv')
        if self.tsv:
            buffer.append('tsv')
        if self.pickle:
            buffer.append('pickle')
        if self.format:
            buffer.append(f'format={Write.ensure_quoted(self.format)}')
        if self.name:
            buffer.append(self.name)
        options = ', '.join(buffer)
        return f'write({options})'

    # AbstractOp

    def setup(self):
        # Determine kind of target
        stdout = False
        var = False
        if self.name_arg is None:
            stdout = True
        else:
            self.name = self.eval_function('name_arg', str)
            if type(self.name) is str:
                if self.name.isidentifier():
                    var = True
                elif not marcel.util.is_filename(self.name):
                    raise marcel.exception.KillCommandException(
                        'If NAME is provided, it must be a Python identifer, or definitely a filename '
                        '(i.e., beginning with ., ~ or /).')
        self.format = self.eval_function('format', str)
        # stdout is incompatible with --pickle
        if stdout and self.pickle:
            raise marcel.exception.KillCommandException(
                '--pickle cannot be specified when writing to stdout.')
        # stdout is incompatible with --append
        if stdout and self.append:
            raise marcel.exception.KillCommandException(
                '--append cannot be specified when writing to stdout.')
        if var and (self.csv or self.tsv or self.pickle or self.format):
            raise marcel.exception.KillCommandException(
                'Text formatting flags cannot be used when writing to a variable.')
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
        if op.name:
            # Writing to file
            path = pathlib.Path(os.path.normpath(op.name)).expanduser()
            mode = 'a' if op.append else 'w'
            self.output = open(path, mode=mode)
        else:
            # Writing to stdout. (If writing to a var, we wouldn't be here.)
            self.output = sys.stdout

    def cleanup(self):
        if self.output != sys.stdout:
            self.output.close()

    def write_line(self, x):
        print(x, file=self.output, flush=True)


class CSVWriter(TextWriter):

    def __init__(self, op, separator):
        assert separator in (COMMA, TAB)
        super().__init__(op)
        self.writer = csv.writer(self,
                                 delimiter=separator,
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
        target = op.name
        picklefile = None
        if type(target) is marcel.reservoir.Reservoir:
            # API
            self.picklefile = target
        elif type(target) is str:
            # API: string is a filename.
            # Interactive: string is a filename or environment variable name.
            if target.isidentifier():
                picklefile = op.getvar(target)
                if type(picklefile) is not marcel.reservoir.Reservoir:
                    if op.append:
                        raise marcel.exception.KillCommandException(
                            f'{target} is not usable as a reservoir, '
                            f'it stores a value of type {type(picklefile)}.')
                    else:
                        picklefile = marcel.reservoir.Reservoir(target)
                        op.env().setvar(target, self.picklefile)
                op.env().mark_possibly_changed(target)
            else:
                picklefile = marcel.picklefile.PickleFile(target)
        elif target is None:
            raise marcel.exception.KillCommandException(f'Reservoir is undefined.')
        else:
            raise marcel.exception.KillCommandException(
                f'{target} is not usable as a reservoir, it stores a value of type {type(picklefile)}.')
        self.writer = picklefile.writer(op.append)
        self.nesting = op.env().vars().n_scopes()

        super().__init__(op)
        self.writer = (marcel.picklefile.PickleFile(op.name).writer(True)
                       if op.append else
                       marcel.picklefile.PickleFile(op.name).writer(False))

    def receive(self, x):
        try:
            self.writer.write(x)
        except:
            self.writer.close()
            raise

    def cleanup(self):
        self.writer.close()
