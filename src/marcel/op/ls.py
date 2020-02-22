"""C{ls [-01rfds] [FILENAME ...]}

Generates a stream of C{osh.file.File}s.

-0                         Do not include the contents of directories.

-1                         Include the contents of only the topmost directories.

-r                         Include the contents of all directories, recursively.

-f                         List files.

-d                         List directories.

-s                         List symlinks.

FILENAME                   Filename or glob pattern.

- Flags 0, 1, r are mutually exclusive. -1 is the default, if none of these flags are specified.
The contents of symlinked directories are never listed.

- Flags f, d, and s may be combined. If none of these flags are specified, then files, directories
and symlinks are all listed.

- If no FILENAME_PATTERNs are provided, then the contents of the current directory are listed.
"""

import argparse
import pathlib

import marcel.core
import marcel.env
import marcel.object.error
import marcel.object.file


def ls():
    return Ls()


class LsArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('ls')
        depth_group = self.add_mutually_exclusive_group()
        depth_group.add_argument('-0', action='store_true', dest='d0')
        depth_group.add_argument('-1', action='store_true', dest='d1')
        depth_group.add_argument('-r', action='store_true', dest='dr')
        self.add_argument('-f', action='store_true', dest='file')
        self.add_argument('-d', action='store_true', dest='dir')
        self.add_argument('-s', action='store_true', dest='symlink')
        self.add_argument('filename', nargs=argparse.REMAINDER)


class Ls(marcel.core.Op):

    argparser = LsArgParser()

    def __init__(self):
        super().__init__()
        self.d0 = False
        self.d1 = False
        self.dr = False
        self.file = False
        self.dir = False
        self.symlink = False
        self.filename = None
        self.emitted = set()

    def __repr__(self):
        if self.d0:
            depth = '0'
        elif self.d1:
            depth = '1'
        else:
            depth = 'recursive'
        include = ''
        if self.file:
            include += 'f'
        if self.dir:
            include += 'd'
        if self.symlink:
            include += 's'
        return ('ls(depth={}, include={}, filename={})'.format(
            depth,
            include,
            [str(p) for p in self.filename]))

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        if not (self.d0 or self.d1 or self.dr):
            self.d0 = True
        if not (self.file or self.dir or self.symlink):
            self.file = True
            self.dir = True
            self.symlink = True
        if len(self.filename) == 0:
            self.filename = [marcel.env.ENV.pwd().as_posix()]

    def receive(self, x):
        assert x is None, x
        for filename in self.filename:
            filename = pathlib.Path(filename).expanduser()
            x = (marcel.env.ENV.pwd() / filename).resolve()
            if x.exists():
                # TODO: Can this be simplified, having visit() do the only directory iteration?
                if x.is_dir():
                    for file in sorted(x.iterdir()):
                        self.visit(file, 0)
                else:
                    self.visit(x, 0)
            else:
                # filename might be a glob. But if it isn't, this still works.
                if filename.startswith('/'):
                    root = pathlib.Path('/')
                    pattern = filename[1:]
                    paths = root.glob(pattern)
                else:
                    paths = marcel.env.ENV.pwd().glob(filename)
                for path in paths:
                    self.visit(path, 0)

    # Op

    def arg_parser(self):
        return Ls.argparser

    # For use by this class

    def visit(self, path, level):
        self.send_path(path)
        if path.is_dir() and ((level == 0 and (self.d1 or self.dr)) or self.dr):
            try:
                for file in sorted(path.iterdir()):
                    self.visit(file, level + 1)
            except PermissionError as e:
                self.send(marcel.object.error.Error('Cannot explore {}: permission denied'.format(path)))

    def send_path(self, path):
        if path.is_file() and self.file or path.is_dir() and self.dir or path.is_symlink() and self.symlink:
            file = marcel.object.file.File(path)
            if file not in self.emitted:
                self.emitted.add(file)
                self.send(file)
