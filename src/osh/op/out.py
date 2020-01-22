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
        self.output = sys.stdout

    def __repr__(self):
        return ('out(append=%s file=%s csv=%s format=%s)' %
                (self.append, self.file, self.csv, Out.ensure_quoted(self.format)))

    # BaseOp

    def doc(self):
        return __doc__

    def setup(self):
        if self.csv and self.format:
            Out.argparser.error('-c/--csv and FORMAT specifications are incompatible')
        output_filename = self.append if self.append else self.file
        if output_filename:
            output_mode = 'a' if self.append else 'w'
            self.output = open(output_filename, mode=output_mode)

    def receive(self, x):
        if self.format:
            try:
                formatted_x = self.format % x
            except Exception as e:
                # If there is one %s in the format, and the object is longer,
                # then convert it to a string
                if self.format.count('%') == 1 and self.format.count('%s') == 1:
                    formatted_x = self.format % str(x)
                else:
                    raise e
        elif self.csv:
            formatted_x = (', '.join([Out.ensure_quoted(x) for x in x])
                           if type(x) in (list, tuple)
                           else str(x))
        else:
            formatted_x = (('(' + Out.ensure_quoted(x[0]) + ',)'
                            if len(x) == 1
                            else '(' + ', '.join([Out.ensure_quoted(x) for x in x]) + ')')
                           if type(x) in (list, tuple)
                           else str(x))
        # Relying on print to provide the \n appears to result in a race condition.
        print(formatted_x, file=self.output)
        self.output.flush()
        self.send(x)

    def receive_complete(self):
        if self.output != sys.stdout:
            self.output.close()
        self.send_complete()

    # Op

    def arg_parser(self):
        return Out.argparser

    # For use by this class

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
