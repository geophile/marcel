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
import sys

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.error
import marcel.object.renderable

Renderable = marcel.object.renderable.Renderable

HELP = '''
{L,wrap=F}out [-a|--append FILENAME] [-f|--file FILENAME] [-c|--csv] [FORMAT]

{L,indent=4:28}{r:-a}, {r:--append}            Append output to the file identified by FILENAME.

{L,indent=4:28}{r:-f}, {r:--file}              Write output to the file identified by FILENAME, replacing an existing
file if necessary.

{L,indent=4:28}{r:-c}, {r:--csv}               Format output as comma-separated values.

{L,indent=4:28}{r:FORMAT}                  The Python formatting specification to be applied to output tuples.


Prints tuples received on the input stream.

Tuples received on the input stream are passed to the output stream. As a side-effect, input
tuples are printed to stdout or to the specified {r:FILENAME}. If the {r:FILENAME} is specified
by {r:--file}, then an existing file is replaced. If the {r:FILENAME} is specified
by {r:--append}, then output is appended to an existing file.

The {r:--append} and {r:--file} options are mutually exclusive.

The {r:--csv} and {r:FORMAT} options are mutually exclusive.
If no formatting options are specified, then the default rendering is used, except
that 1-tuples are unwrapped. (Note that for certain objects, including
{r:File} and {r:Process}, the default rendering is specified by the {n:render_compact()}
or {n:render_full()} methods. Run {n:help object} for more information.)

{n:Error} objects are not subject to formatting specifications, and are not passed on as output.
'''


def out(env, append=None, file=None, csv=False, format=None):
    args = []
    if append:
        args.extend(['--append', append])
    if file:
        args.extend(['--file', file])
    if csv:
        args.append('--csv')
    if format:
        args.append(format)
    return Out(env), args


class OutArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('out', env)
        self.add_flag_one_value('append', '-a', '--append', convert=self.check_str)
        self.add_flag_one_value('file', '-f', '--file', convert=self.check_str)
        self.add_flag_no_value('csv', '-c', '--csv')
        self.add_anon('format', default=None, convert=self.check_str)
        self.at_most_one('csv', 'format')
        self.at_most_one('file', 'append')
        self.validate()


class Out(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.append = None
        self.file = None
        self.csv = False
        self.format = None
        self.output = None
        self.formatter = None

    def __repr__(self):
        return f'out(append={self.append}, file={self.file}, csv={self.csv}, format={Out.ensure_quoted(self.format)})'

    # AbstractOp

    def setup_1(self):
        self.eval_function('append', str)
        self.eval_function('file', str)
        self.eval_function('format', str)
        self.formatter = (PythonFormatter(self) if self.format else
                          CSVFormatter(self) if self.csv else
                          DefaultFormatter(self))

    def receive(self, x):
        self.ensure_output_initialized()
        out = self.formatter.format(x)
        try:
            print(out, file=self.output, flush=True)
        except Exception as e:  # E.g. UnicodeEncodeError
            self.non_fatal_error(input=x, message=str(e))
        finally:
            self.send(x)

    def receive_complete(self):
        self.ensure_output_initialized()
        if self.output != sys.stdout and self.output is not None:
            self.output.close()
        self.send_complete()

    # For use by this class

    def ensure_output_initialized(self):
        if self.output is None:
            self.output = (open(self.append, mode='a') if self.append else
                           open(self.file, mode='w') if self.file else
                           sys.stdout)

    def render(self, x, full):
        if x is None:
            return None
        elif isinstance(x, marcel.object.renderable.Renderable):
            return (x.render_full(self.color_scheme())
                    if full else
                    x.render_compact())
        else:
            return str(x)

    def color_scheme(self):
        return (self.env().color_scheme()
                if self.output == sys.__stdout__ else
                None)

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


class Formatter:

    def __init__(self, op):
        self.op = op

    def format(self, x):
        assert False


class CSVFormatter(Formatter):

    def __init__(self, op):
        super().__init__(op)
        self.writer = csv.writer(self, delimiter=',', quotechar="'", quoting=csv.QUOTE_MINIMAL, lineterminator='')
        self.row = None

    def format(self, x):
        self.writer.writerow(x)
        return self.row

    def write(self, x):
        self.row = x


class PythonFormatter(Formatter):

    def __init__(self, op):
        super().__init__(op)

    def format(self, x):
        return self.op.format.format(*x)


class DefaultFormatter(Formatter):

    def __init__(self, op):
        super().__init__(op)

    def format(self, x):
        if type(x) in (list, tuple):
            if len(x) == 1:
                out = x[0]
                if isinstance(out, Renderable):
                    out = out.render_full(self.op.color_scheme())
            else:
                buffer = []
                for y in x:
                    if isinstance(y, Renderable):
                        y = y.render_compact()
                    buffer.append(Out.ensure_quoted(y))
                out = '(' + ', '.join(buffer) + ')'
        else:
            # TODO: I don't think we can get here.
            assert False, type(x)
            out = str(x)
        return out
