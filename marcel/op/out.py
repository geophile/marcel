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

import sys

import marcel.core
import marcel.object.error
import marcel.object.renderable

SUMMARY = '''
Prints items received on the input stream.
'''

DETAILS = '''
Tuples received on the input stream are passed to the output stream. As a side-effect, input
tuples are printed to stdout or to the file specified by {r:file} or {r:append}.

If no formatting options are specified, then the default rendering is used, except
that 1-tuples are unwrapped.

Error objects are not subject to formatting specifications, and are not passed on as output.
'''


def out(env, append=None, file=None, csv=False, format=None):
    op = Out(env)
    op.append = append
    op.file = file
    op.csv = csv
    op.format = format
    return op


class OutArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('out',
                         env,
                         ['-a', '--append', '-f', '--file', '-c', '--csv'],
                         SUMMARY,
                         DETAILS)
        file_group = self.add_mutually_exclusive_group()
        file_group.add_argument('-a', '--append',
                                help='Append output to the specified file.')
        file_group.add_argument('-f', '--file',
                                help='Write output to the specified file, replacing current contents.')
        self.add_argument('-c', '--csv',
                          action='store_true',
                          help='Generate output in comma-separated value format.')
        self.add_argument('format',
                          nargs='?',
                          help='Python formatting string')


class Out(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.append = None
        self.file = None
        self.csv = False
        self.format = None
        self.output = None

    def __repr__(self):
        return f'out(append={self.append}, file={self.file}, csv={self.csv}, format={Out.ensure_quoted(self.format)})'

    # BaseOp

    def setup_1(self):
        # For some reason, argparse sets file and append to False if neither specified.
        if self.append == False:
            self.append = None
        if self.file == False:
            self.file = None
        super().check_arg(not self.csv or self.format is None,
                          None,
                          'csv=True is incompatible with format specification.')
        super().check_arg(self.file is None or self.append is None,
                          None,
                          'append and file arguments cannot both be specified.')

    def receive(self, x):
        self.ensure_output_initialized()
        if self.format:
            out = self.format.format(*x)
        elif self.csv:
            out = (', '.join([Out.ensure_quoted(y) for y in x])
                   if type(x) in (list, tuple) else
                   str(x))
        else:
            if type(x) in (list, tuple):
                if len(x) == 1:
                    out = x[0]
                    if isinstance(out, marcel.object.renderable.Renderable):
                        out = out.render_full(self.color_scheme())
                else:
                    buffer = []
                    for y in x:
                        if isinstance(y, marcel.object.renderable.Renderable):
                            y = y.render_compact()
                        buffer.append(Out.ensure_quoted(y))
                    out = '(' + ', '.join(buffer) + ')'
            else:
                out = str(x)
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
