""""C{mkdir FILENAME ...}

Creates directories.

FILENAME                   Filename of a directory to be created. The path must not already exist.

For each successfully created directory, the C{File} is written to the output stream. For each
directory that could not be created, an error describing the file is written.
"""
import argparse

import marcel.core
import marcel.object.file
import marcel.op.filenames


def mkdir():
    return Mkdir()


class MkdirArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('mkdir')
        self.add_argument('filename', nargs=argparse.REMAINDER)


class Mkdir(marcel.core.Op):

    argparser = MkdirArgParser()

    def __init__(self):
        super().__init__()
        self.filename = None
        self.paths = None

    def __repr__(self):
        return f'mkdir({self.filename})'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        self.paths = marcel.op.filenames.FilenamesOp.normalize_paths(self.filename)

    def receive(self, _):
        for path in self.paths:
            try:
                path.mkdir(parents=True, exist_ok=False)
                self.send(marcel.object.file.File(path))
            except FileExistsError as e:
                self.send(marcel.object.error.Error(e))

    # Op

    def arg_parser(self):
        return Mkdir.argparser

    def must_be_first_in_pipeline(self):
        return True
