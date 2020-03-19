"""C{cp [SOURCE_FILENAME ...] TARGET_FILENAME}

SOURCE_FILENAME            Filename or glob pattern of a file to be moved.
TARGET_FILENAME            Filename or glob pattern of the destination.

The source files are copied to the target. Even if TARGET_FILENAME is a glob pattern, a single target must be identified.
If there is one source file, then the target may be an existing file, an existing directory, or a path to a non-existent
file. If there are multiple source files, then the target must be an existing directory.

If no SOURCE_FILENAMEs are specified, then the source files are taken from the input stream. In this case,
each input object must be a 1-tuple containing a C{File}, and TARGET_FILENAME must identify a directory that
already exists. (Note that the behavior is based on syntax -- whether SOURCE_FILENAMEs are provided.
If a SOURCE_FILENAME is provided, then source files are not taken from the input stream, even if SOURCE_FILENAME
fails to identify any files.)
"""

import shutil

import marcel.op.filenames


def cp():
    return Cp()


class CpArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('cp')
        self.add_argument('-r', '--recursive', action='store_true')
        self.add_argument('-P', '--preserve-all-symlinks', action='store_true')
        self.add_argument('-H', '--preserve-non-top-symlinks', action='store_true')
        self.add_argument('-L', '--preserve-no-symlinks', action='store_true')
        self.add_argument('-l', '--hard-link-to-source', action='store_true')
        self.add_argument('-s', '--symlink-to-source', action='store_true')
        self.add_argument('-p', '--preserve', action='store_true')
        self.add_argument('filename', nargs='+')


class Cp(marcel.op.filenames.FilenamesOp):

    argparser = CpArgParser()

    def __init__(self):
        super().__init__(op_has_target=True)
        self.recursive = False
        self.preserve_all_symlinks = False
        self.preserve_non_top_symlinks = False
        self.preserve_no_symlinks = False
        self.hard_link_to_source = False
        self.symlink_to_source = False

    def __repr__(self):
        return f'cp({self.filename})'

    # BaseOp

    def doc(self):
        return __doc__

    # Op

    def arg_parser(self):
        return Cp.argparser

    # FilenamesOp

    def action(self, source):
        if marcel.op.filenames.FilenamesOp.is_path_dir(source):
            if self.target.exists():
                if marcel.op.filenames.FilenamesOp.is_path_file(source):
                    raise marcel.exception.KillAndResumeException(
                        self, source, f'Cannot copy a directory to a file: {self.target}')
                elif marcel.op.filenames.FilenamesOp.is_path_dir(source):
                    # The source directory is copied into the target directory.
                    # Cases:
                    # - Target directory has no path with the source's name (i.e., the last segment of the path):
                    #      - Copy recursively into the target.
                    # - Target directory has a file matching the source's name:
                    #      - Error: can't copy directory over file.
                    # - Target directory has a directory matching the source's name:
                    #      - Recursively copy source contents into the target/sourcename directory.
                    pass
            else:
                try:
                    shutil.copytree(source, self.target_posix)
                except shutil.Error as e:
                    raise marcel.exception.KillAndResumeException(self, source, e)
        else:
            shutil.copy(source.as_posix(), self.target_posix)
