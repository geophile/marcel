import pathlib
import time

import marcel.env
import marcel.object.renderable
from marcel.util import *

DIR_MASK = 0o040000
FILE_MASK = 0o100000
LINK_MASK = 0o120000
FILE_TYPE_MASK = DIR_MASK | FILE_MASK | LINK_MASK


class File(marcel.object.renderable.Renderable):
    """Represents a file or directory.
    """

    def __init__(self, path, base=None):
        assert path is not None
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        self.path = path
        self.display_path = path.relative_to(base) if base else path
        self.os_stat = None

    def __repr__(self):
        return self.render_compact()

    def __getattr__(self, attr):
        return getattr(self.path, attr)

    # Renderable

    def render_compact(self):
        return str(self.display_path)

    def render_full(self, color):
        line = self._formatted_metadata()
        if color:
            line[-1] = colorize(line[-1], self._highlight_color(self))
        if self.is_symlink():
            line.append('->')
            link_target = self.resolve()
            if color:
                link_target = colorize(link_target, self._highlight_color(link_target))
            if isinstance(link_target, pathlib.Path):
                link_target = link_target.as_posix()
            line.append(link_target)
        return ' '.join(line)

    # For use by this class

    def _formatted_metadata(self):
        lstat = self.lstat()  # Not stat. Don't want to follow symlinks here.
        return [
            self._mode_string(lstat.st_mode),
            ' ',
            '{:8s}'.format(username(lstat.st_uid)),
            '{:8s}'.format(groupname(lstat.st_gid)),
            '{:12}'.format(lstat.st_size),
            ' ',
            self._formatted_mtime(lstat.st_mtime),
            ' ',
            self.display_path.as_posix()]

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

    @staticmethod
    def _highlight_color(path):
        extension = path.suffix.lower()
        color_scheme = marcel.env.ENV.color_scheme()
        highlight = color_scheme.file_extension.get(extension)
        if highlight is None:
            highlight = (
                # which must check path.resolve(), not path. If the path is relative, and the name
                # is also an executable on PATH, then highlighting will be incorrect. See bug 8.
                color_scheme.file_executable if is_executable(path.resolve().as_posix()) else
                color_scheme.file_link if path.is_symlink() else
                color_scheme.file_dir if path.is_dir() else
                color_scheme.file_file)
        return highlight

    @staticmethod
    def _rwx(m):
        buffer = [
            'r' if (m & 0o4) != 0 else '-',
            'w' if (m & 0o2) != 0 else '-',
            'x' if (m & 0o1) != 0 else '-'
        ]
        return ''.join(buffer)
