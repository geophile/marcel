"""C{out [-a|--append FILENAME] [-f|--file FILENAME] [-c | --csv | FORMAT]}

Input objects are passed on as output. As a side-effect, input objects are
printed to stdout or to a file. The output is rendered using the default
converstion to string unless specified otherwise.

-a | --append FILENAME     Append to the named file.

-f | --file FILENAME       Write to the named file, overwriting an existing
                           file if it exists.

-c | --csv                 Format output separating components by commas.
                           Each component is rendered using the default conversion
                           to string.

FORMAT                     A Python formatter specifying how an object should be
                           rendered.
"""

import sys

import marcel.core
import marcel.object.error
import marcel.object.renderable


def out():
    return Out()


class OutArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('out')
        file_group = self.add_mutually_exclusive_group()
        file_group.add_argument('-a', '--append', required=False)
        file_group.add_argument('-f', '--file', required=False)
        self.add_argument('-c', '--csv', action='store_true')
        self.add_argument('format', nargs='?')


class Out(marcel.core.Op):
    argparser = OutArgParser()

    def __init__(self):
        super().__init__()
        self.append = None
        self.file = None
        self.csv = False
        self.format = None
        self.output = None

    def __repr__(self):
        return ('out(append=%s file=%s csv=%s format=%s)' %
                (self.append, self.file, self.csv, Out.ensure_quoted(self.format)))

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        if self.csv and self.format:
            Out.argparser.error('-c/--csv and FORMAT specifications are incompatible')

    def receive(self, x):
        self.ensure_output_initialized()
        if self.format:
            try:
                out = self.format % x
            except Exception as e:
                # TODO: This sucks. At least check for the right exception: TypeError
                # If there is one %s in the format, and the object is longer,
                # then convert it to a string
                if self.format.count('%') == 1 and self.format.count('%s') == 1:
                    out = self.format % str(x)
                else:
                    raise e
        elif self.csv:
            out = (', '.join([Out.ensure_quoted(y) for y in x])
                   if type(x) in (list, tuple) else
                   str(x))
        else:
            if type(x) in (list, tuple):
                if len(x) == 1:
                    out = x[0]
                    if isinstance(out, marcel.object.renderable.Renderable):
                        out = out.render_full(self.use_color())
                else:
                    buffer = []
                    for y in x:
                        if isinstance(y, marcel.object.renderable.Renderable):
                            y = y.render_compact()
                        buffer.append(Out.ensure_quoted(y))
                    out = '(' + ', '.join(buffer) + ')'
            else:
                out = str(x)
        # Relying on print to provide the \n appears to result in a race condition.
        try:
            print(out, file=self.output, flush=True)
        except Exception as e:  # E.g. UnicodeEncodeError
            error = marcel.object.error.Error(e)
            self.print_error(error)
        finally:
            self.send(x)

    def receive_error(self, error):
        self.ensure_output_initialized()
        self.print_error(error)

    def receive_complete(self):
        self.ensure_output_initialized()
        if self.output != sys.stdout and self.output is not None:
            self.output.close()
        self.send_complete()

    # Op

    def arg_parser(self):
        return Out.argparser

    # For use by this class

    def ensure_output_initialized(self):
        if self.output is None:
            self.output = (open(self.append, mode='a') if self.append else
                           open(self.file, mode='w') if self.file else
                           sys.stdout)

    def print_error(self, error):
        print(self.render(error, True), file=self.output, flush=True)

    def render(self, x, full):
        if x is None:
            return None
        elif isinstance(x, marcel.object.renderable.Renderable):
            return (x.render_full(self.use_color())
                    if full else
                    x.render_compact())
        else:
            return str(x)

    def use_color(self):
        return self.output == sys.__stdout__

    @staticmethod
    def ensure_quoted(x):
        if x is None:
            return 'None'
        elif type(x) in (int, float):
            return str(x)
        elif isinstance(x, str):
            if "'" not in x:
                return "'%s'" % x
            elif '"' not in x:
                return '"%s"' % x
            else:
                return "'%s'" % x.replace("'", "\\'")
        else:
            return str(x)
