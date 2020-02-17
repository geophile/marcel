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

import osh.core
import osh.env
from osh.util import *


def out():
    return Out()


class OutArgParser(osh.core.OshArgParser):

    def __init__(self):
        super().__init__('out')
        file_group = self.add_mutually_exclusive_group()
        file_group.add_argument('-a', '--append', required=False)
        file_group.add_argument('-f', '--file', required=False)
        self.add_argument('-c', '--csv', action='store_true')
        self.add_argument('format', nargs='?')


class Out(osh.core.Op):
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

    # def __getstate__(self):
    #     self.output = None
    #     return self.__dict__
    #
    # def __setstate__(self, state):
    #     self.__dict__.update(state)
    #     self.initialize_output()

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        if self.csv and self.format:
            Out.argparser.error('-c/--csv and FORMAT specifications are incompatible')
        # self.ensure_output_initialized()

    def receive(self, x):
        self.ensure_output_initialized()
        if self.format:
            try:
                formatted = self.format % x
            except Exception as e:
                # If there is one %s in the format, and the object is longer,
                # then convert it to a string
                if self.format.count('%') == 1 and self.format.count('%s') == 1:
                    formatted = self.format % str(x)
                else:
                    raise e
        elif self.csv:
            if type(x) in (list, tuple):
                formatted = ', '.join([Out.ensure_quoted(x) for x in x])
            else:
                formatted = str(x)
        else:
            if type(x) in (list, tuple):
                if len(x) == 1:
                    formatted = '(' + Out.ensure_quoted(x[0]) + ',)'
                else:
                    formatted = '(' + ', '.join([Out.ensure_quoted(x) for x in x]) + ')'
            else:
                formatted = str(x)
        # Relying on print to provide the \n appears to result in a race condition.
        try:
            print(formatted, file=self.output, flush=True)
        except Exception as e:  # E.g. UnicodeEncodeError
            error = osh.core.OshError(e)
            self.print_error(error)
        finally:
            self.send(x)

    def receive_error(self, error):
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
        print(error, file=self.output, flush=True)

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
