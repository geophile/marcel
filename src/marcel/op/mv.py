"""C{mv [SOURCE_FILENAME ...] TARGET_FILENAME}

SOURCE_FILENAME            Filename or glob pattern of a file to be moved.
TARGET_FILENAME            Filename or glob pattern of the destination.

The source files are moved to the target. Even if TARGET_FILENAME is a glob pattern, a single target must be identified.
If there is one source file, then the target may be an existing file, an existing directory, or a path to a non-existent
file. If there are multiple source files, then the target must be an existing directory.

If no SOURCE_FILENAMEs are specified, then the source files are taken from the input stream. In this case,
each input object must be a 1-tuple containing a C{File}, and TARGET_FILENAME must identify a directory that
already exists. (Note that the behavior is based on syntax -- whether SOURCE_FILENAMEs are provided.
If a SOURCE_FILENAME is provided, then source files are not taken from the input stream, even if SOURCE_FILENAME
fails to identify any files.)
"""

import shutil

import marcel.op.filenames


def mv():
    return Mv()


class MvArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('mv')
        self.add_argument('filename', nargs='+')


class Mv(marcel.op.filenames.FilenamesOp):

    argparser = MvArgParser()

    def __init__(self):
        super().__init__(op_has_target=True)

    def __repr__(self):
        return f'mv({self.filename})'

    # BaseOp

    def doc(self):
        return __doc__

    # Op

    def arg_parser(self):
        return Mv.argparser

    # FilenamesOp

    def action(self, source):
        try:
            shutil.move(source.as_posix(), self.target_posix)
        except FileExistsError as e:
            raise marcel.exception.KillAndResumeException(self, source, str(e))
