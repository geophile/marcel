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

import marcel.exception
import marcel.object.renderable
import marcel.util

DIR_MASK = 0o040000
FILE_MASK = 0o100000
LINK_MASK = 0o120000
FILE_TYPE_MASK = DIR_MASK | FILE_MASK | LINK_MASK
MISSING = object()


class MetadataCache:
    
    def __init__(self):
        self.id_to_name = {}

    def user_and_group_names(self, uid, gid):
        key = (uid, gid)
        username, groupname = self.id_to_name.get(key, (MISSING, MISSING))
        if username is MISSING:
            # groupname is MISSING too
            username = marcel.util.username(uid)
            groupname = marcel.util.groupname(gid)
            self.id_to_name[key] = (username, groupname)
        return username, groupname
        

class File(marcel.object.renderable.Renderable):

    def __init__(self, path, base=None, metadata_cache=None):
        assert path is not None
        self.metadata_cache = metadata_cache
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        self.path = path
        self.base = base
        self.compact_path = None
        self.lstat = None
        self.executable = None
        # Used only to survive pickling
        self.path_str = None
        self.base_str = None

    def __getattr__(self, attr):
        return getattr(self.path, attr)

    def __getstate__(self):
        # Ensure metadata is present before transmission
        self._is_executable()
        self._lstat()
        state = self.__dict__.copy()
        state['compact_path'] = None
        # Send strings, not paths
        if self.path is not None:
            state['path_str'] = str(self.path)
            state['path'] = None
        if self.base is not None:
            state['base_str'] = str(self.base)
            state['base'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        if self.path_str:
            self.path = pathlib.Path(self.path_str)
            self.path_str = None
        if self.base_str:
            self.base = pathlib.Path(self.base_str)
            self.base_str = None

    def __hash__(self):
        return self.path.__hash__()

    def __eq__(self, other):
        return self.path == other.path

    def __ne__(self, other):
        return self.path != other.path

    def __lt__(self, other):
        return self.path < other.path

    def __le__(self, other):
        return self.path <= other.path

    def __gt__(self, other):
        return self.path > other.path

    def __ge__(self, other):
        return self.path >= other.path

    # Renderable

    def render_compact(self):
        return str(self._compact_path())

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

    def unlink(self):
        # unlink(missing_ok=True) requires Python >= 3.8
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        return self.path

    # For use by this class

    def _is_executable(self):
        # is_executable must check path.resolve(), not path. If the path is relative, and the name
        # is also an executable on PATH, then highlighting will be incorrect. See bug 8.
        if self.executable is None:
            self.executable = marcel.util.is_executable(self.path.resolve().as_posix())
        return self.executable

    def _formatted_metadata(self):
        lstat = self._lstat()  # Not stat. Don't want to follow symlinks here.
        username, groupname = self._user_and_group_names(lstat.st_uid, lstat.st_gid)
        return [
            self._mode_string(lstat.st_mode),
            ' ',
            '{:6s}'.format(username),
            '{:6s}'.format(groupname),
            '{:8}'.format(lstat.st_size),
            ' ',
            self._formatted_mtime(lstat.st_mtime),
            ' ',
            self._compact_path().as_posix()]

    def _lstat(self):
        if self.lstat is None:
            try:
                self.lstat = self.path.lstat()
            except FileNotFoundError:
                raise marcel.exception.KillAndResumeException(f'{self.path} does not exist.')
        return self.lstat

    def _user_and_group_names(self, uid, gid):
        if self.metadata_cache:
            return self.metadata_cache.user_and_group_names(uid, gid)
        else:
            # File not created via ls command
            return marcel.util.username(uid), marcel.util.groupname(gid)

    def _compact_path(self):
        if self.compact_path is None:
            self.compact_path = self.path.relative_to(self.base) if self.base else self.path
        return self.compact_path

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
            extension = path.suffix.lower()[1:]  # Get rid of the leading dot provided by Path.suffix.
            highlight = (color_scheme.file_extension.get(extension, None)
                         if type(color_scheme.file_extension) is dict else
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
