"""C{rm [FILENAME ...]}

FILENAME                   Filename or glob pattern.

Files (including directories) are removed. They can be specified in one of two ways:

1) Specify one or more FILENAMEs, (or glob patterns).

2) Specify no FILENAMEs, in which case the files to be removed are piped in from the preceding
command in the pipeline. Each incoming objects must be a 1-tuple containing a C{File}.

E.g. to remove all the .pyc files in the current directory:

    C{rm *.pyc}

or

    C{ls *.pyc | rm}
"""

import shutil

import marcel.core
import marcel.object.error
import marcel.object.file
import marcel.op.filenames


def rm():
    return Rm()


class RmArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('rm')
        self.add_argument('filename', nargs='*')


class Rm(marcel.op.filenames.FilenamesOp):

    argparser = RmArgParser()

    def __init__(self):
        super().__init__(op_has_target=False)

    def __repr__(self):
        return f'rm({self.filename})'

    # BaseOp

    def doc(self):
        return __doc__

    # Op

    def arg_parser(self):
        return Rm.argparser

    # FilenameOp

    def action(self, source):
        try:
            if source.is_dir():
                shutil.rmtree(source)
            else:  # This works for files and symlinks
                source.unlink()
        except PermissionError as e:
            self.send(marcel.object.error.Error(e))
        except FileNotFoundError:
            pass
