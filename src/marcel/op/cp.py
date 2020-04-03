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

import os.path
import pathlib
import shutil
import sys

import marcel.op.filenames

FilenamesOp = marcel.op.filenames.FilenamesOp
FilenamesOpActions = marcel.op.filenames.FilenamesOpActions
PathType = marcel.op.filenames.PathType
LinkFollow = marcel.op.filenames.LinkFollow
classify_source = marcel.op.filenames.classify_source
classify_target = marcel.op.filenames.classify_target


def cp():
    return Cp()


class CpArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('cp')
        self.add_argument('-r', '--recursive', action='store_true')
        follow_links = self.add_mutually_exclusive_group()
        follow_links.add_argument('-N', '--follow-symlink-never', action='store_true')
        follow_links.add_argument('-T', '--follow-symlink-top', action='store_true')
        follow_links.add_argument('-A', '--follow-symlink-always', action='store_true')
        create_links = self.add_mutually_exclusive_group()
        create_links.add_argument('-l', '--hard-link-to-source', action='store_true')
        create_links.add_argument('-s', '--symlink-to-source', action='store_true')
        # TODO: self.add_argument('-p', '--preserve', action='store_true')
        self.add_argument('filename', nargs='+')


class Cp(marcel.op.filenames.FilenamesOp):
    argparser = CpArgParser()

    source_to_file_actions = FilenamesOpActions(
        'cp',
        action_map={

        })

    def __init__(self):
        super().__init__(op_has_target=True)
        self.recursive = False
        self.follow_symlink_never = False
        self.follow_symlink_always = False
        self.follow_symlink_top = False
        self.hard_link_to_source = False
        self.symlink_to_source = False
        self.follow_symlink_unspecified = False

    def __repr__(self):
        return f'cp({self.filename})'

    # BaseOp

    def setup_1(self):
        super().setup_1()
        self.follow_symlink_unspecified = not (self.follow_symlink_never or
                                               self.follow_symlink_always or
                                               self.follow_symlink_top)

    def doc(self):
        return __doc__

    # Op

    def arg_parser(self):
        return Cp.argparser

    # FilenamesOp

    def action(self, source):
        self.copy(source, True, self.target)

    # For use by this class

    def copy(self, source, source_is_top, target):
        source_classification = classify_source(source, is_top=source_is_top)
        target_classification = classify_target(target)
        if PathType.is_nothing(source_classification):  # does not exist
            raise marcel.exception.KillAndResumeException(self, source, 'No such file or directory')
        if PathType.is_link(source_classification) and not self.follow_link(source_classification):
            self.copy_link(source, target, target_classification)
        elif PathType.is_file(source_classification):  # file or link to file that should be followed
            self.copy_file(source, target, target_classification)
        elif PathType.is_dir(source_classification):  # dir or link to dir that should be followed
            self.copy_dir(source, source_classification, target, target_classification)
        else:
            assert False, source

    def copy_link(self, source, target, target_classification):
        # Linux cp -P will copy a symlink over: a file; symlink to a file; a symlink to nothing.
        # shutil.copy will raise FileExistsError if the target exists and follow_symlink is False.
        # So remove the file or symlink to prevent the exception.
        if (PathType.is_file(target_classification) or
                PathType.is_link(target_classification) and PathType.is_nothing(target_classification)):
            target.unlink()
        shutil.copy(source.as_posix(), target.as_posix(), follow_symlinks=False)

    def copy_file(self, source, target, target_classification):
        target_is_dangling_link = (PathType.is_link(target_classification) and
                                   PathType.is_nothing(target_classification) and not
                                   target.exists())
        if target_is_dangling_link:
            raise marcel.exception.KillAndResumeException(self, source, f'Cannot write through dangling link: {target}')
        shutil.copy(source.as_posix(), target.as_posix(), follow_symlinks=True)

    def copy_dir(self, source, source_classification, target, target_classification):
        target_is_dangling_link = (PathType.is_link(target_classification) and
                                   PathType.is_nothing(target_classification) and not
                                   target.exists())
        if target_is_dangling_link or PathType.is_file(target_classification):
            raise marcel.exception.KillAndResumeException(self, source, f'Cannot overwrite non-directory: {target}')
        if Cp.related(source, target):
            raise marcel.exception.KillAndResumeException(
                self, source, f'Cannot copy a directory to it\'s ancestor or descendent: {target}')
        if target.exists():
            sub_target = target / source.name
            if sub_target.exists():
                # Copy files
                sub_target.mkdir(exist_ok=True)
                for sub_source in source.iterdir():
                    self.copy(sub_source, False, sub_target)
            else:
                shutil.copytree(source.as_posix(),
                                sub_target.as_posix(),
                                symlinks=not self.follow_link(source_classification))
        else:
            shutil.copytree(source.as_posix(),
                            target.as_posix(),
                            symlinks=not self.follow_link(source_classification))

    def follow_link(self, source_classification):
        return (self.follow_symlink_always or
                self.follow_symlink_top and PathType.is_top_link(source_classification) or
                self.follow_symlink_unspecified
                and PathType.is_link(source_classification)
                and PathType.is_file(source_classification))

    @staticmethod
    def related(p, q):
        p = p.resolve().as_posix()
        q = q.resolve().as_posix()
        return p.startswith(q) or q.startswith(p)
