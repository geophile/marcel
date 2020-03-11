"""C{mv [SOURCE_FILENAME ...] TARGET_FILENAME}

SOURCE_FILENAME            Filename or glob pattern of a file to be moved.
TARGET_FILENAME            Filename or glob pattern of the destination.

The source files are moved to the target. Even if TARGET_FILENAME is a glob pattern, a single target must be identified.
If there is one source file, then the target may be an existing file, an existing directory, or a path to a non-existent
file. If there are multiple source files, then the target must be an existing directory.

If no SOURCE_FILENAMEs are specified, then the source files are taken from the input stream. In this case,
each input object must be a 1-tuple containing a C{FILE}, and TARGET_FILENAME must identify a directory that
already exists. (Note that the behavior is based on syntax -- whether SOURCE_FILENAMEs are provided.
If a SOURCE_FILENAME is provided, then source files are not taken from the input stream, even if SOURCE_FILENAME
fails to identify any files.)
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
        self.roots = []
        self.target = None
        self.target_posix = None

    def __repr__(self):
        return f'mv({self.filename})'

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        self.current_dir = self.global_state().env.pwd()
        targets = marcel.op.filenames.roots(self.current_dir, self.filename[-1:])
        if len(targets) > 1:
            raise marcel.exception.KillCommandException(f'Cannot specify multiple targets: {self.filename[-1]}')
        self.target = (targets[0] if len(targets) == 1 else pathlib.Path(self.filename[-1])).resolve()
        self.target_posix = self.target.as_posix()
        target_path = pathlib.Path(self.target).resolve()  # Follows symlink if possible
        sources = self.filename[:-1]
        if len(sources) == 0:
            if not target_path.is_dir():
                raise marcel.exception.KillCommandException(
                    f'{self.target} must be a directory if files to be moved are provided via input pipe')
            self.roots = None
        else:
            self.roots = marcel.op.filenames.roots(self.current_dir, sources)
            if target_path.exists():
                if target_path.is_file():
                    if len(self.roots) > 1:
                        raise marcel.exception.KillCommandException('Cannot move multiple sources to a file target')
            else:
                if len(self.roots) > 1:
                    raise marcel.exception.KillCommandException('Cannot move multiple sources to a non-existent target')

    def receive(self, x):
        try:
            if self.roots is None:
                if len(x) != 1 and not isinstance(x[0], marcel.object.file.File):
                    raise marcel.exception.KillAndResumeException(self, x, 'Input to mv is not a File')
                self.move(x[0].path)
            else:
                for root in self.roots:
                    samefile = self.target.exists() and root.samefile(self.target)
                    if root.is_dir() and samefile:
                        raise marcel.exception.KillAndResumeException(
                            self, root, f'Cannot move directory into self: {root}')
                    elif root.is_file() and samefile:
                        raise marcel.exception.KillAndResumeException(
                            self, root, f'Cannot move file over self: {root}')
                    else:
                        self.move(root)
        except shutil.Error as e:
            raise marcel.exception.KillAndResumeException(self, x, str(e))

    # Op

    def arg_parser(self):
        return Mv.argparser

    def must_be_first_in_pipeline(self):
        # This is checked before setup_1 converts empty source to None.
        return len(self.roots) > 0

    # For use by this class

    def move(self, path):
        shutil.move(path.as_posix(), self.target_posix)
