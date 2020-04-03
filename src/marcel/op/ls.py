"""C{ls [-01rfds] [FILENAME ...]}

Generates a stream of C{osh.file.File}s.

-0                         Do not include the contents of topmost directories.

-1                         Include the contents of only the topmost directories.

-r | --recursive           Include the contents of directories, recursively.

-f                         List files.

-d                         List directories.

-s                         List symlinks.

FILENAME                   Filename or glob pattern.

- Flags 0, 1, r are mutually exclusive. -1 is the default, if none of these flags are specified.
The contents of symlinked directories are never listed.

- Flags f, d, and s may be combined. If none of these flags are specified, then files, directories
and symlinks are all listed.

- If no FILENAMEs are provided, then . is assumed.
"""

import argparse
import sys

import marcel.core
import marcel.object.error
import marcel.object.file
import marcel.op.filenames


def ls():
    return Ls()


class LsArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('ls', ['-0', '-1', '-r', '-f', '--file', '-d', '--dir', '-s', '--symlink'])
        depth_group = self.add_mutually_exclusive_group()
        depth_group.add_argument('-0', action='store_true', dest='d0')
        depth_group.add_argument('-1', action='store_true', dest='d1')
        depth_group.add_argument('-r', '--recursive', action='store_true', dest='dr')
        self.add_argument('-f', '--file', action='store_true')
        self.add_argument('-d', '--dir', action='store_true')
        self.add_argument('-s', '--symlink', action='store_true')
        self.add_argument('filename', nargs=argparse.REMAINDER)


class Ls(marcel.op.filenames.FilenamesOp):

    argparser = LsArgParser()

    def __init__(self):
        super().__init__(op_has_target=False)
        self.d0 = False
        self.d1 = False
        self.dr = False
        self.file = False
        self.dir = False
        self.symlink = False
        self.base = None
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
        filenames = [str(p) for p in self.filename] if self.filename else '?'
        return f'ls(depth={depth}, include={include}, filename={filenames})'

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        super().setup_1()
        if self.roots is None:
            self.roots = [self.current_dir]
        if not (self.d0 or self.d1 or self.dr):
            self.d1 = True
        if not (self.file or self.dir or self.symlink):
            self.file = True
            self.dir = True
            self.symlink = True
        if len(self.roots) == 1:
            root = self.roots[0]
            if root.is_dir():
                self.base = root
            else:
                self.base = root.parent
        else:
            self.base = None
        self.roots = sorted(self.roots)

    # Op

    def arg_parser(self):
        return Ls.argparser

    def must_be_first_in_pipeline(self):
        return True

    # FilenamesOp

    def action(self, source):
        self.visit(source, 0)

    # For use by this class

    def visit(self, root, level):
        self.send_path(root)
        if root.is_dir() and ((level == 0 and (self.d1 or self.dr)) or self.dr):
            for file in sorted(root.iterdir()):
                try:
                    self.visit(file, level + 1)
                except PermissionError:
                    self.send(marcel.object.error.Error(f'Cannot explore {root}: permission denied'))

    def send_path(self, path):
        s = marcel.op.filenames.FilenamesOp.is_path_symlink(path)
        f = marcel.op.filenames.FilenamesOp.is_path_file(path)
        d = marcel.op.filenames.FilenamesOp.is_path_dir(path)
        if ((self.file and f) or (self.dir and d) or (self.symlink and s)) and path not in self.emitted:
            file = marcel.object.file.File(path, self.base)
            self.send(file)
            self.emitted.add(path)
