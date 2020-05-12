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
import stat
import time

import marcel.object.renderable
import marcel.op.filenames
import marcel.util

DIR_MASK = 0o040000
FILE_MASK = 0o100000
LINK_MASK = 0o120000
FILE_TYPE_MASK = DIR_MASK | FILE_MASK | LINK_MASK


class File(marcel.object.renderable.Renderable):

    def __init__(self, path, base=None):
        assert path is not None
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        self.path = path
        self.display_path = path.relative_to(base) if base else path
        self.lstat = None
        self.executable = None
        # Used only to survive pickling
        self.path_str = None
        self.display_path_str = None

    def __repr__(self):
        return self.render_compact()

    def __getattr__(self, attr):
        return getattr(self.path, attr)

    def __getstate__(self):
        # Ensure metadata is present before transmission
        self._is_executable()
        self._lstat()
        # Send strings, not paths
        if self.path is not None:
            self.path_str = str(self.path)
            self.path = None
        if self.display_path is not None:
            self.display_path_str = str(self.display_path)
            self.display_path = None
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)
        if self.path_str:
            self.path = pathlib.Path(self.path_str)
            self.path_str = None
        if self.display_path_str:
            self.display_path = pathlib.Path(self.display_path_str)
            self.display_path_str = None

    # Renderable

    def render_compact(self):
        return str(self.display_path)

    def render_full(self, color_scheme):
        line = self._formatted_metadata()
        # line[-1] is the filename.
        line[-1] = marcel.util.colorize(line[-1], self._highlight_color(self, color_scheme))
        if self._is_symlink():
            line.append('->')
            link_target = pathlib.Path(os.readlink(self.path))
            link_target = marcel.util.colorize(link_target,
                                               self._highlight_color(link_target, color_scheme))
            if isinstance(link_target, pathlib.Path):
                link_target = link_target.as_posix()
            line.append(link_target)
        return ' '.join(line)

    # File

    mode = property(lambda self: self._lstat()[0])
    inode = property(lambda self: self._lstat()[1])
    device = property(lambda self: self._lstat()[2])
    links = property(lambda self: self._lstat()[3])
    uid = property(lambda self: self._lstat()[4])
    gid = property(lambda self: self._lstat()[5])
    size = property(lambda self: self._lstat()[6])
    atime = property(lambda self: self._lstat()[7])
    mtime = property(lambda self: self._lstat()[8])
    ctime = property(lambda self: self._lstat()[9])

    def read(self):
        with self.path.open(mode='r') as file:
            return file.read()

    def readlines(self):
        with self.path.open(mode='r') as file:
            return [line.rstrip('\r\n') for line in file.readlines()]

    # For use by this class

    def _is_executable(self):
        # is_executable must check path.resolve(), not path. If the path is relative, and the name
        # is also an executable on PATH, then highlighting will be incorrect. See bug 8.
        if self.executable is None:
            self.executable = marcel.util.is_executable(self.path.resolve().as_posix())
        return self.executable

    def _formatted_metadata(self):
        lstat = self._lstat()  # Not stat. Don't want to follow symlinks here.
        return [
            self._mode_string(lstat.st_mode),
            ' ',
            '{:8s}'.format(marcel.util.username(lstat.st_uid)),
            '{:8s}'.format(marcel.util.groupname(lstat.st_gid)),
            '{:12}'.format(lstat.st_size),
            ' ',
            self._formatted_mtime(lstat.st_mtime),
            ' ',
            self.display_path.as_posix()]

    def _lstat(self):
        if self.lstat is None:
            self.lstat = self.path.lstat()
        return self.lstat

    @staticmethod
    def _mode_string(mode):
        buffer = [
            'l' if (mode & LINK_MASK) == LINK_MASK else
            'd' if (mode & DIR_MASK) == DIR_MASK else
            '-',
            File._rwx((mode & 0o700) >> 6),
            File._rwx((mode & 0o70) >> 3),
            File._rwx(mode & 0o7)
        ]
        return ''.join(buffer)

    @staticmethod
    def _formatted_mtime(mtime):
        return time.strftime('%Y %b %d %H:%M:%S', time.localtime(mtime))

    def _highlight_color(self, path, color_scheme):
        highlight = None
        if color_scheme:
            extension = path.suffix.lower()
            highlight = (color_scheme.file_extension.get(extension, None)
                         if color_scheme.file_extension is dict else
                         None)
            if highlight is None:
                highlight = (
                    # Check symlink first, because is_executable (at least) follows symlinks.
                    color_scheme.file_link if self._is_symlink() else
                    color_scheme.file_executable if self._is_executable() else
                    color_scheme.file_dir if self._is_dir() else
                    color_scheme.file_file)
        return highlight

    # Use stat.S_... methods instead of methods relying on pathlib. First, pathlib
    # doesn't cache lstat results. Second, if the file has been transmitted as part
    # of a sudo command, then the recipient can't necessarily run lstat.

    def _is_symlink(self):
        return stat.S_ISLNK(self._lstat().st_mode)

    def _is_dir(self):
        return stat.S_ISDIR(self._lstat().st_mode)

    @staticmethod
    def _rwx(m):
        return (('r' if (m & 0o4) != 0 else '-') +
                ('w' if (m & 0o2) != 0 else '-') +
                ('x' if (m & 0o1) != 0 else '-'))
