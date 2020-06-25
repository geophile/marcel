# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import os
import pathlib

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.error
import marcel.object.file


HELP = '''
{L,wrap=F}ls [[-01] [-r|--recursive]] [-f|--file] [-d|--dir] [-s|--symlink] [FILENAME ...]

{L,indent=4:28}{r:-0}                      Include only files matching the specified FILENAMEs, (i.e., depth 0).

{L,indent=4:28}{r:-1}                      Include files matching the specified FILENAMEs, and in any directories
among the FILENAMEs, (i.e., depth 1).

{L,indent=4:28}{r:-r}, {r:--recursive}         Include all files contained in the identified FILENAMEs, recursively,
to any depth.

{L,indent=4:28}{r:-f}, {r:--file}              Include files in output.

{L,indent=4:28}{r:-d}, {r:--dir}               Include directories in output.

{L,indent=4:28}{r:-s}, {r:--symlink}           Include symbolic links in output.

{L,indent=4:28}{r:FILENAME}                A filename or glob pattern.

Generates a stream of {n:File} objects, representing files, directories and symlinks.

The flags {r:-0}, {r:-1}, and {r:-r} are mutually exclusive. {r:-1} is the default.

Flags {r:-f}, {r:-d}, and {r:-s} may be combined. If none of these flags are specified, then files, directories
and symbolic links are all listed.

If no {r:FILENAME}s are provided, then the current directory is listed.

Run {n:help file} for more information on {n:File} objects.
'''


def ls(env, *paths, depth=None, recursive=False, file=False, dir=False, symlink=False):
    args = []
    if depth == 0:
        args.append('-0')
    elif depth == 1:
        args.append('-1')
    if recursive:
        args.append('--recursive')
    if file:
        args.append('--file')
    if dir:
        args.append('--dir')
    if symlink:
        args.append('--symlink')
    args.extend(paths)
    return Ls(env), args


class LsArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('ls', env)
        self.add_flag_no_value('d0', '-0', None)
        self.add_flag_no_value('d1', '-1', None)
        self.add_flag_no_value('dr', '-r', '--recursive')
        self.add_flag_no_value('file', '-f', '--file')
        self.add_flag_no_value('dir', '-d', '--dir')
        self.add_flag_no_value('symlink', '-s', '--symlink')
        self.add_anon_list('filenames', convert=self.check_str)
        self.at_most_one('d0', 'd1', 'dr')
        self.validate()


class Ls(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.d0 = False
        self.d1 = False
        self.dr = False
        self.file = False
        self.dir = False
        self.symlink = False
        self.filenames = None
        self.current_dir = None
        self.roots = None
        self.base = None
        self.emitted = None
        self.metadata_cache = None

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
        filenames = [str(p) for p in self.filenames] if self.filenames else '?'
        return f'ls(depth={depth}, include={include}, filename={filenames})'

    # AbstractOp

    def setup_1(self):
        self.eval_function('filenames', str, pathlib.Path)
        self.roots = []
        self.current_dir = self.env().dir_state().pwd()
        self.roots = Ls.deglob(self.current_dir, self.filenames)
        if len(self.filenames) > 0 and len(self.roots) == 0:
            raise marcel.exception.KillCommandException(f'No qualifying paths: {self.filenames}')
        self.emitted = set()
        if len(self.roots) == 0:
            self.roots = [self.current_dir]
        if not (self.d0 or self.d1 or self.dr):
            self.d1 = True
        if not (self.file or self.dir or self.symlink):
            self.file = True
            self.dir = True
            self.symlink = True
        self.roots = sorted(self.roots)
        self.determine_base()
        self.metadata_cache = marcel.object.file.MetadataCache()

    # Op

    def receive(self, _):
        for root in self.roots:
            self.visit(root, 0)

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    def visit(self, root, level):
        self.send_path(root)
        if root.is_dir() and ((level == 0 and (self.d1 or self.dr)) or self.dr):
            try:
                for file in sorted(root.iterdir()):
                    self.visit(file, level + 1)
            except PermissionError:
                self.non_fatal_error(input=root, message='Permission denied')
            except FileNotFoundError:
                self.non_fatal_error(input=root, message='No such file or directory')

    def send_path(self, path):
        s = path.is_symlink()
        f = path.is_file() and not s
        d = path.is_dir() and not s
        if ((self.file and f) or (self.dir and d) or (self.symlink and s)) and path not in self.emitted:
            file = marcel.object.file.File(path, self.base, self.metadata_cache)
            self.send(file)
            self.emitted.add(path)

    def determine_base(self):
        # nca: nearest common ancestor
        nca_parts = None
        nca = None  # index into nearest_common_ancestor
        for root in self.roots:
            root_parts = root.parts
            if nca_parts is None:
                nca_parts = root_parts
                nca = len(nca_parts)
            else:
                limit = min(len(root_parts), nca)
                i = 0
                while i < limit and nca_parts[i] == root_parts[i]:
                    i += 1
                nca = i
        self.base = pathlib.Path('/' + '/'.join(nca_parts[1:nca]))
        if self.base.is_file():
            self.base = self.base.parent

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
        paths = Ls.normalize_paths(filenames)
        roots = []
        roots_set = set()
        for path in paths:
            # Proceed as if path is a glob pattern, but this works for non-globs too.
            path_str = path.as_posix()
            glob_base, glob_pattern = ((pathlib.Path('/'), path_str[1:])
                                       if path.is_absolute() else
                                       (current_dir, path_str))
            for root in glob_base.glob(glob_pattern):
                if root not in roots_set:
                    roots_set.add(root)
                    roots.append(root)
        return roots
