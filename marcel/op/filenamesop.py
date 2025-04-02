# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
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
import types

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.error
import marcel.object.file
import marcel.op.filenames

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

    def __init__(self, action):
        super().__init__()
        # A method's type would be MethodType. We don't want a method of this class, e.g. self.foobar. self
        # would be bound to the current instance, and that might not be the instance that gets executed later,
        # due to possible pipelines copying. The action should not be a method, e.g. it could be a staticmethod,
        # whose type is FunctionType.
        assert isinstance(action, types.FunctionType)
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
        # emitted_paths is maintained to avoid visiting the same path repeatedly, as might happen
        # with roots containing wildcards. E.g., a? and ?f would both identify a file names ax.
        self.emitted_paths = None
        # Set of visited directories, used to avoid revisiting directories via symlinks. Directories
        # are identified by (stat.st_dev, stat.st_ino).
        self.visited_dirs = None
        self.metadata_cache = None
        self.formatting = None

    # AbstractOp

    def setup(self, env):
        self.filenames = self.eval_function(env, 'filenames_arg', str, pathlib.Path, pathlib.PosixPath, File)
        self.roots = []
        self.current_dir = pathlib.Path(env.dir_state().current_dir())
        self.roots = marcel.op.filenames.Filenames(env, self.filenames).normalize()
        if len(self.filenames) > 0 and len(self.roots) == 0:
            raise marcel.exception.KillCommandException(f'No qualifying paths, (possibly due to permission errors):'
                                                        f' {self.filenames}')
        self.emitted_paths = set()
        self.visited_dirs = set()
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
        self.formatting = marcel.object.file.FileFormatting()

    # Op

    def run(self, env):
        for root in self.roots:
            try:
                self.visit(env, root, 0)
            except marcel.exception.KillAndResumeException:
                pass

    # For use by this class

    def visit(self, env, root, level):
        file = File(root, self.base, self.metadata_cache)
        file.adjust_formatting(self.formatting)
        self.action(self, env, file)
        if root.is_dir() and ((level == 0 and (self.d1 or self.dr)) or self.dr) and not self.dir_already_visited(root):
            try:
                root_stat = root.stat()
                self.visited_dirs.add((root_stat.st_dev, root_stat.st_ino))
                sorted_dir_contents = sorted(root.iterdir())
                for file in sorted_dir_contents:
                    try:
                        self.visit(env, file, level + 1)
                    except PermissionError:
                        self.non_fatal_error(env, input=file, message='Permission denied')
                    except FileNotFoundError:
                        self.non_fatal_error(env, input=file, message='No such file or directory')
                    except marcel.exception.KillAndResumeException:
                        pass
            except PermissionError:
                self.non_fatal_error(env, input=root, message='Permission denied')
            except FileNotFoundError:
                self.non_fatal_error(env, input=root, message='No such file or directory')
            except marcel.exception.KillAndResumeException:
                pass

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

    def dir_already_visited(self, path):
        # There could be multiple paths to a directory due to symlinks. Check if path is a symlink to a directory
        # that has already been visited.
        assert path.is_dir(), path
        if path.is_symlink():
            target = path.resolve()
            target_stat = target.stat()
            target_id = (target_stat.st_dev, target_stat.st_ino)
            if target_id in self.visited_dirs:
                return True
        return False
