"""File-handling ops: ls, mv, cp, ln, rm have similar filename arguments:
- Zero or more SOURCE_FILENAMEs, where each SOURCE_FILENAME is a filename or glob.
- Zero or one TARGET_FILENAME (also a filename or glob).
- If there are zero SOURCE_FILENAMEs, then input files arrive as input from upstream.

ls and rm have just SOURCE_FILENAMEs.

This base class centralizes a lot of logic for these ops
"""

import os
import pathlib
import shutil

import marcel.core
import marcel.exception
import marcel.object.file


class FilenamesOp(marcel.core.Op):

    def __init__(self, op_has_target):
        super().__init__()
        self.op_has_target = op_has_target
        self.filename = None
        self.current_dir = None
        self.roots = []
        if self.op_has_target:
            self.target = None
            self.target_posix = None

    # BaseOp

    def setup_1(self):
        self.current_dir = self.global_state().env.pwd()
        self.find_roots_and_target()

    def receive(self, x):
        try:
            if self.roots is None:
                if len(x) != 1 and not isinstance(x[0], marcel.object.file.File):
                    raise marcel.exception.KillAndResumeException(self, x, 'Input must be a File')
                self.action(x[0].path)
            else:
                if x is not None:
                    raise marcel.exception.KillCommandException(
                        f'{self.op_name()} has sources, so it cannot receive input from a pipe')
                if self.op_has_target:
                    if len(self.roots) == 0:
                        filenames = ', '.join(self.filename)
                        raise marcel.exception.KillCommandException(f'No such file or directory: {filenames}')
                    for root in self.roots:
                        samefile = self.target.exists() and root.samefile(self.target)
                        if FilenamesOp.is_path_dir(root) and samefile:
                            raise marcel.exception.KillAndResumeException(
                                self, root, f'Source and target must be different directories: {root}')
                        elif FilenamesOp.is_path_file(root) and samefile:
                            raise marcel.exception.KillAndResumeException(
                                self, root, f'Source and target must be different files: {root}')
                        else:
                            self.action(root)
                else:
                    for root in self.roots:
                        self.action(root)
        except shutil.Error as e:
            raise marcel.exception.KillAndResumeException(self, x, str(e))

    # Op

    def must_be_first_in_pipeline(self):
        # This is checked before setup_1 converts empty source to None.
        return len(self.roots) > 0

    # FilenamesOp

    def action(self, source):
        assert False

    # For use by this class

    def find_roots_and_target(self):
        if self.op_has_target:
            if len(self.filename) == 0:
                raise marcel.exception.KillCommandException('No target specified')
            targets = FilenamesOp.deglob(self.current_dir, self.filename[-1:])
            last_filename = self.filename[-1]
            if len(targets) > 1:
                raise marcel.exception.KillCommandException(f'Cannot specify multiple targets: {last_filename}')
            # If targets is empty, it's because last_filename did not identify any existing paths. So treat
            # last_filename as a non-existent target.
            self.target = targets[0] if len(targets) == 1 else pathlib.Path(last_filename)
            target_path = pathlib.Path(self.target).resolve()  # Follows symlink if possible
            sources = self.filename[:-1]
            if len(sources) == 0:
                if not FilenamesOp.is_path_dir(target_path):
                    raise marcel.exception.KillCommandException(
                        f'{self.target} must be a directory if no SOURCE_FILENAMEs are specified.')
                self.roots = None
            else:
                self.roots = self.deglob(self.current_dir, sources)
                if target_path.exists():
                    if FilenamesOp.is_path_file(target_path):
                        if len(self.roots) > 1:
                            raise marcel.exception.KillCommandException(
                                'Cannot use multiple sources with a file target')
                else:
                    if len(self.roots) > 1:
                        raise marcel.exception.KillCommandException(
                            'Cannot use multiple sources with a non-existent target')
            self.target_posix = self.target.as_posix()
        else:
            self.roots = None if len(self.filename) == 0 else FilenamesOp.deglob(self.current_dir, self.filename)

    @staticmethod
    def normalize_paths(filenames):
        # Resolve ~
        # Resolve . and ..
        # Convert to Path
        paths = []
        for filename in filenames:
            # Resolve . and ..
            filename = os.path.normpath(filename)
            # Convert to Path and resolve ~
            path = pathlib.Path(filename).expanduser()
            # If path is relative, specify what it is relative to.
            if not path.is_absolute():
                path = pathlib.Path.cwd() / path
            paths.append(path)
        return paths

    @staticmethod
    def deglob(current_dir, filenames):
        # Expand globs and eliminate duplicates
        paths = FilenamesOp.normalize_paths(filenames)
        roots = []
        roots_set = set()
        for path in paths:
            # Proceed as if path is a glob pattern, but this should work for non-globs too. I haven't
            # measured the impact on performance.
            path_str = path.as_posix()
            glob_base, glob_pattern = ((pathlib.Path('/'), path_str[1:])
                                       if path.is_absolute() else
                                       (current_dir, path_str))
            for root in glob_base.glob(glob_pattern):
                if root not in roots_set:
                    roots_set.add(root)
                    roots.append(root)
        return roots

    # pathlib.is_file() and is_dir() return True for symlinks also, which is usually misleading
    # for filename ops. So use these instead.

    @staticmethod
    def is_path_file(path):
        return path.is_file() and not path.is_symlink()

    @staticmethod
    def is_path_dir(path):
        return path.is_dir() and not path.is_symlink()

    @staticmethod
    def is_path_symlink(path):
        return path.is_symlink()


class PathType:

    # A path description is expressed in four bits:
    # 0, 1: type of resolved path (i.e., after following links) -- does not exist, file, or dir.
    # 2:    path is a link
    # 3:    path is topmost (i.e., a root of a filenames op, such as cp or ls).
    UNDETERMINED         = 0x0      # Path type not determined
    NOTHING              = 0x1      # Resolved path does not exist.
    FILE                 = 0x2      # Resolved path is a file.
    DIR                  = 0x3      # Resolved path is a dir.
    LINK                 = 0x4      # Unresolved path is a link.
    TOP                  = 0x8      # Unresolved path is topmost (i.e. a root for a filename op)
    LINK_TO_NOTHING      = LINK | NOTHING
    LINK_TO_FILE         = LINK | FILE
    LINK_TO_DIR          = LINK | DIR
    TOP_LINK_TO_NOTHING  = TOP | LINK | NOTHING
    TOP_LINK_TO_FILE     = TOP | LINK | FILE
    TOP_LINK_TO_DIR      = TOP | LINK | DIR
    FILE_TYPE_MASK       = 0x3
    OPTION_BITS          = 4
    DISPATCH_TABLE_SIZE = 1 << OPTION_BITS

    @staticmethod
    def is_nothing(classification):
        return classification & PathType.FILE_TYPE_MASK == PathType.NOTHING

    @staticmethod
    def is_file(classification):
        return classification & PathType.FILE_TYPE_MASK == PathType.FILE

    @staticmethod
    def is_dir(classification):
        return classification & PathType.FILE_TYPE_MASK == PathType.DIR

    @staticmethod
    def is_link(classification):
        return classification & PathType.LINK != 0

    @staticmethod
    def is_top_link(classification):
        mask = PathType.LINK | PathType.TOP
        return classification & mask == mask


class LinkFollow:

    ALWAYS = 1
    NEVER = 2
    TOP_ONLY = 3


class CircularLinkException(Exception): pass


def not_implemented(source, target):
    raise NotImplementedError()


def _classify(path, is_top):
    try:
        resolved = path.resolve(strict=True)
        if resolved.is_file():
            classification = PathType.FILE
        elif resolved.is_dir():
            classification = PathType.DIR
        elif resolved.is_link():
            assert False
        else:
            raise marcel.exception.KillAndResumeException(None, path, 'Unrecognized file type')
    except FileNotFoundError:
        classification = PathType.NOTHING
    except RuntimeError:
        raise CircularLinkException(path)
    if path.is_symlink():
        classification |= PathType.LINK
    if is_top:
        classification |= PathType.TOP
    return classification


def classify_source(path, is_top):
    return _classify(path, is_top)


def classify_target(path):
    return _classify(path, False)
