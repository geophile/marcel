"""C{mv [SOURCE_FILENAME] ... TARGET_FILENAME}

SOURCE_FILENAME            Filename or glob pattern of a file to be moved.
TARGET_FILENAME            Filename or glob pattern of the destination.

The source files are moved to the target. Even if TARGET_FILENAME is a glob pattern, a single target must be identified.
If there is one source file, then the target may be an existing file, an existing directory, or a path to a non-existent
file. If there are multiple source files, then the target must be an existing directory.

If no SOURCE_FILENAMEs are specified, then the source files are taken from the input stream. In this case, each input
object must be a 1-tuple containing a C{FILE}, and TARGET_FILENAME must identify a directory that already exists.
"""

import pathlib
import shutil

import marcel.core
import marcel.object.error
import marcel.object.file
import marcel.op.filenames


def mv():
    return Mv()


class MvArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('mv')
        self.add_argument('filename', nargs='+')


class Mv(marcel.core.Op):

    argparser = MvArgParser()

    def __init__(self):
        super().__init__()
        self.current_dir = None
        self.filename = None
        self.source = []
        self.target = None
        self.target_posix = None

    def __repr__(self):
        return f'mv({self.filename})'

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        self.current_dir = self.global_state().env.pwd()
        self.source = self.filename[:-1]
        self.target = pathlib.Path(self.filename[-1]).resolve()
        self.target_posix = self.target.as_posix()
        target_path = pathlib.Path(self.target).resolve()  # Follows symlink
        if len(self.source) == 0:
            if not target_path.is_dir():
                raise marcel.exception.KillCommandException(f'{self.target} is not a directory')
            self.source = None
        else:
            if target_path.exists():
                if target_path.is_file():
                    if len(self.source) > 1:
                        raise marcel.exception.KillCommandException('Cannot move multiple sources to a file target')
            else:
                if len(self.source) > 1:
                    raise marcel.exception.KillCommandException('Cannot move multiple sources to a non-existent target')

    def receive(self, x):
        try:
            if self.source is None:
                # Move files passed in
                if len(x) != 1 or not isinstance(x[0], marcel.object.file.File):
                    raise marcel.exception.KillAndResumeException('mv input must be a 1-tuple containing a File')
                self.move(x[0].path)
            else:
                paths = marcel.op.filenames.normalize_paths(self.source)
                roots = marcel.op.filenames.roots(self.current_dir, paths)
                for root in roots:
                    if root.is_dir() and root.samefile(self.target):
                        self.send(marcel.object.error.Error(f'Cannot move directory over self: {root}'))
                    else:
                        self.move(root)
        except shutil.Error as e:
            raise marcel.exception.KillAndResumeException(self, x, str(e))

    # Op

    def arg_parser(self):
        return Mv.argparser

    def must_be_first_in_pipeline(self):
        # This is checked before setup_1 converts empty source to None.
        return len(self.source) > 0

    # For use by this class

    def move(self, path):
        shutil.move(path.as_posix(), self.target_posix)
