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

File = marcel.object.file.File


class FilenamesOpArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, op_name, env):
        super().__init__(op_name, env)
        self.add_flag_no_value('d0', '-0', None)
        self.add_flag_no_value('d1', '-1', None)
        self.add_flag_no_value('dr', '-r', '--recursive')
        self.add_anon_list('filenames', convert=self.check_str_or_file, target='filenames_arg')
        self.at_most_one('d0', 'd1', 'dr')


class FilenamesOp(marcel.core.Op):

    def __init__(self, env, action):
        super().__init__(env)
        self.action = action
        self.d0 = False
        self.d1 = False
        self.dr = False
        self.file = False
        self.dir = False
        self.symlink = False
        self.filenames_arg = None
        self.filenames = None
        self.current_dir = None
        self.roots = None
        self.base = None
        self.emitted = None
        self.metadata_cache = None

    # AbstractOp

    def setup(self):
        self.filenames = self.eval_function('filenames_arg', str, pathlib.Path, pathlib.PosixPath, File)
        self.roots = []
        self.current_dir = self.env().dir_state().pwd()
        self.roots = self.deglob()
        if len(self.filenames) > 0 and len(self.roots) == 0:
            raise marcel.exception.KillCommandException(f'No qualifying paths, (possibly due to permission errors):'
                                                        f' {self.filenames}')
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

    # For use by this class

    def visit(self, root, level):
        file = File(root, self.base, self.metadata_cache)
        self.action(self, file)
        if root.is_dir() and ((level == 0 and (self.d1 or self.dr)) or self.dr):
            try:
                for file in sorted(root.iterdir()):
                    self.visit(file, level + 1)
            except PermissionError:
                self.non_fatal_error(input=root, message='Permission denied')
            except FileNotFoundError:
                self.non_fatal_error(input=root, message='No such file or directory')

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

    def normalize_paths(self):
        # Resolve ~
        # Resolve . and ..
        # Convert to Path
        paths = []
        for filename in self.filenames:
            if type(filename) is File:
                filename = filename.path
            # Resolve . and ..
            filename = os.path.normpath(filename)
            # Convert to Path and resolve ~
            path = pathlib.Path(filename).expanduser()
            # If path is relative, specify what it is relative to.
            if not path.is_absolute():
                path = pathlib.Path.cwd() / path
            paths.append(path)
        return paths

    def deglob(self):
        # Expand globs and eliminate duplicates
        paths = self.normalize_paths()
        roots = []
        roots_set = set()
        for path in paths:
            # Proceed as if path is a glob pattern, but this works for non-globs too.
            path_str = path.as_posix()
            glob_base, glob_pattern = ((pathlib.Path('/'), path_str[1:])
                                       if path.is_absolute() else
                                       (self.current_dir, path_str))
            for root in (glob_base.glob(glob_pattern)
                         if len(glob_pattern) > 0 else
                         glob_base.iterdir()):
                if root not in roots_set:
                    roots_set.add(root)
                    roots.append(root)
        return roots
