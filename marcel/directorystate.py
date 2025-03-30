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

import marcel.exception
import marcel.util


class DirectoryState:

    def __init__(self, env):
        self.env = env

    def __repr__(self):
        return f'DirectoryState({self._dir_stack()})'

    def current_dir(self):
        self._clean_dir_stack()
        return pathlib.Path(self.env.getvar('PWD'))

    def change_current_dir(self, directory):
        if isinstance(directory, str):
            directory = pathlib.Path(directory)
        isinstance(directory, pathlib.Path), directory
        # current_dir() calls _clean_dir_stack(),
        new_dir = (self.current_dir() / directory.expanduser()).resolve(False)  # False: due to bug 27
        dir_stack = self._dir_stack()
        if new_dir.exists():
            new_dir = new_dir.as_posix()
            # So that executables have the same view of the current directory.
            os.chdir(new_dir)
            if len(dir_stack) == 0:
                dir_stack.append(new_dir)
            else:
                dir_stack[-1] = new_dir
            self.env.namespace['PWD'] = new_dir
        else:
            home = pathlib.Path.home().resolve()
            marcel.util.print_to_stderr(self.env,
                                        f'Directory {new_dir} does not exist, '
                                        f'going to home directory instead: {home}')
            if len(dir_stack) == 0 or dir_stack[-1] != home:
                self.push_dir(home)

    def push_dir(self, directory):
        self._clean_dir_stack()
        # Operate on a copy of the directory stack. Don't want to change the
        # actual stack until the cd succeeds (bug 133).
        dir_stack = list(self._dir_stack())
        if directory is None:
            if len(dir_stack) > 1:
                dir_stack[-2:] = [dir_stack[-1], dir_stack[-2]]
        else:
            assert isinstance(directory, pathlib.Path)
            dir_stack.append(directory.resolve().as_posix())
        self.change_current_dir(pathlib.Path(dir_stack[-1]))
        self.env.namespace['DIRS'] = dir_stack

    def pop_dir(self):
        self._clean_dir_stack()
        dir_stack = self._dir_stack()
        if len(dir_stack) > 1:
            self.change_current_dir(pathlib.Path(dir_stack[-2]))
            dir_stack.pop()

    def reset_dir_stack(self):
        dir_stack = self._dir_stack()
        dir_stack.clear()
        dir_stack.append(self.current_dir())

    def dirs(self):
        self._clean_dir_stack()
        dirs = list(self._dir_stack())
        dirs.reverse()
        return dirs

    def _dir_stack(self):
        return self.env.getvar('DIRS')

    # Remove entries that are not files, and not accessible, (presumably due to changes since they entered the stack).
    def _clean_dir_stack(self):
        clean = []
        removed = []
        dirs = self._dir_stack()
        for dir in dirs:
            if isinstance(dir, pathlib.Path):
                dir = dir.as_posix()
            if os.path.exists(dir) and os.access(dir, mode=os.X_OK, follow_symlinks=True):
                clean.append(dir)
            else:
                removed.append(dir)
        if len(removed) > 0:
            self.env.namespace['DIRS'] = clean
            buffer = ['The following directories have been removed from the directory stack because',
                      'they are no longer accessible:']
            buffer.extend(removed)
            message = '\n'.join(buffer)
            marcel.util.print_to_stderr(self.env, message)
