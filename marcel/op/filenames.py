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


# - Expand globs
# - Make paths absolute
# - Resolve ~
# - Resolve . and ..
# - Eliminate duplicates
# - Convert to pathlib.Path

class Filenames(object):

    def __init__(self, env, filenames):
        self.filenames = filenames
        # Marcel and host path should be in sync. Use os.getcwd() instead of DirState to minimize dependence
        # on Environment. This works better for API and farcel usage.
        self.current_dir = pathlib.Path(os.getcwd())

    def normalize(self):
        # Expand globs and eliminate duplicates
        paths = self._normalize_paths()
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

    def _normalize_paths(self):
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
                path = self.current_dir / path
            paths.append(path)
        return paths
