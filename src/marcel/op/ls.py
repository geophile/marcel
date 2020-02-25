"""C{ls [-01rfds] [FILENAME ...]}

Generates a stream of C{osh.file.File}s.

-0                         Do not include the contents of topmost directories.

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

- If no FILENAMEs are provided, then . is assumed.
"""

import argparse
import os.path
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
        return ('ls(depth={}, include={}, filename={})'.format(
            depth,
            include,
            [str(p) for p in self.filename]))

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        if not (self.d0 or self.d1 or self.dr):
            self.d1 = True
        if not (self.file or self.dir or self.symlink):
            self.file = True
            self.dir = True
            self.symlink = True
        if len(self.filename) == 0:
            self.filename = [marcel.env.ENV.pwd().as_posix()]

    def receive(self, _):
        paths = self.paths()
        roots = Ls.roots(paths)
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

    def paths(self):
        # Resolve ~
        # Resolve . and ..
        # Convert to Path
        # Eliminate duplicates
        paths = []
        path_set = set()  # For avoiding duplicates
        for i in range(len(self.filename)):
            # Resolve . and ..
            filename = os.path.normpath(self.filename[i])
            # Convert to Path and resolve ~
            path = pathlib.Path(filename).expanduser()
            # Make absolute. Don't use Path.resolve(), which follows symlinks.
            if not path.is_absolute():
                path = pathlib.Path.cwd() / path
            if path not in path_set:
                paths.append(path)
                path_set.add(path)
        return paths

    @staticmethod
    def roots(paths):
        roots = []
        current_dir = marcel.env.ENV.pwd()
        for path in paths:
            if path.exists():
                roots.append(path)
            else:
                path_str = path.as_posix()
                glob_base, glob_pattern = ((pathlib.Path('/'), path_str[1:])
                                           if path.is_absolute() else
                                           (current_dir, path_str))
                for root in sorted(glob_base.glob(glob_pattern)):
                    roots.append(root)
        return roots

    def visit(self, root, level, base):
        self.send_path(root, base)
        if root.is_dir() and ((level == 0 and (self.d1 or self.dr)) or self.dr):
            try:
                for file in sorted(root.iterdir()):
                    self.visit(file, level + 1, base)
            except PermissionError:
                self.send(marcel.object.error.Error('Cannot explore {}: permission denied'.format(root)))

    def send_path(self, path, base):
        if path.is_file() and self.file or path.is_dir() and self.dir or path.is_symlink() and self.symlink:
            file_id = Ls.fileid(path)
            file = marcel.object.file.File(path, base)
            if file_id not in self.emitted:
                self.emitted.add(file_id)
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
