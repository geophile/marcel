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
import os.path
import pathlib

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
        self.current_dir = None
        self.emitted = set()  # Contains (device, inode)

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
        self.current_dir = self.global_state().env.pwd()
        if not (self.d0 or self.d1 or self.dr):
            self.d1 = True
        if not (self.file or self.dir or self.symlink):
            self.file = True
            self.dir = True
            self.symlink = True
        if len(self.filename) == 0:
            self.filename = [self.current_dir.as_posix()]

    def receive(self, _):
        roots = marcel.op.filenames.FilenamesOp.deglob(self.current_dir, self.filename)
        # Paths will be displayed relative to a root if there is one root and it is a directory.
        base = roots[0] if len(roots) == 1 and roots[0].is_dir() else None
        for root in sorted(roots):
            self.visit(root, 0, base)

    # Op

    def arg_parser(self):
        return Ls.argparser

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    def visit(self, root, level, base):
        self.send_path(root, base)
        if root.is_dir() and ((level == 0 and (self.d1 or self.dr)) or self.dr):
            try:
                for file in sorted(root.iterdir()):
                    self.visit(file, level + 1, base)
            except PermissionError:
                self.send(marcel.object.error.Error(f'Cannot explore {root}: permission denied'))

    def send_path(self, path, base):
        if path.is_file() and self.file or path.is_dir() and self.dir or path.is_symlink() and self.symlink:
            file = marcel.object.file.File(path, base)
            self.send(file)

    @staticmethod
    def find_base(roots):
        base = None
        if len(roots) > 0:
            base_parts = roots[0].parts
            for root in roots:
                common = 0
                root_parts = root.parts
                for i in range(min(len(base_parts), len(root_parts))):
                    if base_parts[common] == root_parts[common]:
                        common += 1
                    else:
                        break
                base_parts = base_parts[:common]
            if len(base_parts) > 0:
                base = pathlib.Path().joinpath(*base_parts)
        return base

    @staticmethod
    def fileid(path):
        stat = os.lstat(path)
        return stat.st_dev, stat.st_ino
