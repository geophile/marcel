"""File-handling ops: mv, cp, ln, rm have similar filename arguments:
- Zero or more SOURCE_FILENAMEs, where each SOURCE_FILENAME is a filename or glob.
- Exactly one TARGET_FILENAME (also a filename or glob), (except for rm which has no target).
- If there are zero SOURCE_FILENAMEs, then input files arrive as input from upstream.

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
                    for root in self.roots:
                        samefile = self.target.exists() and root.samefile(self.target)
                        if root.is_dir() and samefile:
                            raise marcel.exception.KillAndResumeException(
                                self, root, f'Source and target must be different directories: {root}')
                        elif root.is_file() and samefile:
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
            targets = FilenamesOp.deglob(self.current_dir, self.filename[-1:])
            if len(targets) > 1:
                raise marcel.exception.KillCommandException(f'Cannot specify multiple targets: {self.filename[-1]}')
            self.target = (targets[0] if len(targets) == 1 else pathlib.Path(self.filename[-1])).resolve()
            # TODO: Symlink handling is more complicated: HPL flags on cp.
            target_path = pathlib.Path(self.target).resolve()  # Follows symlink if possible
            sources = self.filename[:-1]
            if len(sources) == 0:
                if not target_path.is_dir():
                    raise marcel.exception.KillCommandException(
                        f'{self.target} must be a directory if no SOURCE_FILENAMEs are specified.')
                self.roots = None
            else:
                self.roots = self.deglob(self.current_dir, sources)
                if target_path.exists():
                    if target_path.is_file():
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
    def deglob(current_dir, filenames):
        paths = FilenamesOp.normalize_paths(filenames)
        roots = []
        roots_set = set()
        for path in paths:
            if path.exists():
                roots.append(path)
            else:
                path_str = path.as_posix()
                glob_base, glob_pattern = ((pathlib.Path('/'), path_str[1:])
                                           if path.is_absolute() else
                                           (current_dir, path_str))
                for root in glob_base.glob(glob_pattern):
                    if root not in roots_set:
                        roots_set.add(root)
                        roots.append(root)
        return roots

    @staticmethod
    def normalize_paths(filenames):
        # Resolve ~
        # Resolve . and ..
        # Convert to Path
        # Eliminate duplicates
        paths = []
        path_set = set()  # For avoiding duplicates
        for i in range(len(filenames)):
            # Resolve . and ..
            filename = os.path.normpath(filenames[i])
            # Convert to Path and resolve ~
            path = pathlib.Path(filename).expanduser()
            # Make absolute. Don't use Path.resolve(), which follows symlinks.
            if not path.is_absolute():
                path = pathlib.Path.cwd() / path
            if path not in path_set:
                paths.append(path)
                path_set.add(path)
        return paths
