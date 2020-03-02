"""C{mv SOURCE_FILENAME ... TARGET_FILENAME}

SOURCE_FILENAME            Filename or glob pattern of a file to be moved.
TARGET_FILENAME            Filename or glob pattern of the destination.

The source files are moved to the target. Even if TARGET_FILENAME is a glob pattern, a single target must be identified.
If there is one source file, then the target may be an existing file, an existing directory, or a path to a non-existent
file. If there are multiple source files, then the target must be an existing directory.
"""

import argparse
import pathlib
import shutil

import marcel.core
import marcel.env
import marcel.object.error
import marcel.object.file
import marcel.op.filenames


def mv():
    return Mv()


class MvArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('mv')
        self.add_argument('filename', nargs=argparse.REMAINDER)


class Mv(marcel.core.Op):

    argparser = MvArgParser()

    def __init__(self):
        super().__init__()
        self.filename = None
        self.source = []
        self.target = None

    def __repr__(self):
        return 'mv({})'.format(self.filename)

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        if len(self.filename) < 2:
            raise marcel.exception.KillCommandException('mv must specify at least one source and exactly one target')
        self.source = self.filename[:-1]
        self.target = pathlib.Path(self.filename[-1]).resolve()
        target_path = pathlib.Path(self.target).resolve()  # Follows symlink
        if target_path.exists():
            if target_path.is_file():
                if len(self.source) > 1:
                    raise marcel.exception.KillCommandException('Cannot move multiple sources to a file target')
        else:
            if len(self.source) > 1:
                raise marcel.exception.KillCommandException('Cannot move multiple sources to a non-existent target')

    def receive(self, _):
        paths = marcel.op.filenames.normalize_paths(self.source)
        roots = marcel.op.filenames.roots(marcel.env.ENV.pwd(), paths)
        for root in roots:
            if root.is_dir() and root.samefile(self.target):
                self.send(marcel.object.error.Error('Cannot move directory over self: {}'.format(root)))
            else:
                shutil.move(root.as_posix(), self.target.as_posix())

    # Op

    def arg_parser(self):
        return Mv.argparser

    def must_be_first_in_pipeline(self):
        return True
