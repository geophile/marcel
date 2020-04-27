import os
import pathlib
import shutil

import marcel.core
import marcel.exception
import marcel.object.file


class FilenamesOp(marcel.core.Op):

    def __init__(self, op_has_target):
        super().__init__()
        self.filename = None
        self.current_dir = None
        self.roots = []

    # BaseOp

    def setup_1(self):
        self.current_dir = self.env().dir_state().pwd()
        self.roots = FilenamesOp.deglob(self.current_dir, self.filename)
        if len(self.filename) > 0 and len(self.roots) == 0:
            raise marcel.exception.KillCommandException(f'No qualifying paths: {self.filename}')

    def receive(self, _):
        for root in self.roots:
            self.action(root)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # FilenamesOp

    def action(self, source):
        assert False

    # For use by this class

    def find_roots(self):
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
