import pathlib
import shutil

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

    def __init__(self, directory, file=None):
        # Restrictive requirements that I may want to relax later
        assert isinstance(directory, pathlib.Path), directory
        assert directory.is_absolute(), directory
        if file and not isinstance(file, pathlib.Path):
            file = pathlib.Path(file)
            assert not file.is_absolute(), file
        self.dir = directory
        self.file = file
        self.path = directory / file if file else directory
        self.os_stat = None

    def __repr__(self):
        return self.render_compact()

    def __eq__(self, other):
        return self.path.as_posix() == other.path.as_posix()

    def __ne__(self, other):
        return self.path.as_posix() != other.path.as_posix()

    def __lt__(self, other):
        return self.path.as_posix() < other.path.as_posix()

    def __le__(self, other):
        return self.path.as_posix() <= other.path.as_posix()

    def __gt__(self, other):
        return self.path.as_posix() > other.path.as_posix()

    def __ge__(self, other):
        return self.path.as_posix() >= other.path.as_posix()

    def __hash__(self):
        return self.path.as_posix().__hash__()

    abspath = property(lambda self: self.path.as_posix(),
                       doc="""Absolute path to this file.""")
    stat = property(lambda self: self._stat(),
                    doc="""Information on this file, as returned by C{os.stat}.""")
    mode = property(lambda self: self._stat()[0],
                    doc="""mode of this file.""")
    inode = property(lambda self: self._stat()[1],
                     doc="""inode of this file.""")
    device = property(lambda self: self._stat()[2],
                      doc="""device of this file.""")
    links = property(lambda self: self._stat()[3],
                     doc=""" Number of links of this file.""")
    uid = property(lambda self: self._stat()[4],
                   doc="""Owner of this file.""")
    gid = property(lambda self: self._stat()[5],
                   doc="""Owning group of this file.""")
    size = property(lambda self: self._stat()[6],
                    doc="""Size of this file (bytes).""")
    atime = property(lambda self: self._stat()[7],
                     doc="""Access time of this file.""")
    mtime = property(lambda self: self._stat()[8],
                     doc="""Modify time of this file.""")
    ctime = property(lambda self: self._stat()[9],
                     doc="""Change time of this file.""")
    isdir = property(lambda self: self.mode & FILE_TYPE_MASK == DIR_MASK,
                     doc="""True iff this file is a directory.""")
    isfile = property(lambda self: self.mode & FILE_TYPE_MASK == FILE_MASK,
                      doc="""True iff this file is neither a directory nor a symlink.""")
    islink = property(lambda self: self.mode & FILE_TYPE_MASK == LINK_MASK,
                      doc="""True iff this file is a symlink.""")

    # Renderable

    def render_compact(self):
        return self.abspath

    def render_full(self, color):
        line = self._formatted_metadata()
        if color:
            line[-1] = colorize(line[-1], self._highlight_color())
        return ' '.join(line)

    # For use by this class

    def _stat(self):
        if self.os_stat is None:
            self.os_stat = self.path.lstat()
        return self.os_stat

    def _mode_string(self):
        mode = self.mode
        buffer = [
            'l' if (mode & LINK_MASK) == LINK_MASK else
            'd' if (mode & DIR_MASK) == DIR_MASK else
            '-',
            File._rwx((mode & 0o700) >> 6),
            File._rwx((mode & 0o70) >> 3),
            File._rwx(mode & 0o7)
        ]
        return ''.join(buffer)

    def _highlight_color(self):
        extension = self.path.suffix.lower()
        color_scheme = marcel.env.ENV.color_scheme()
        highlight = color_scheme.file_extension.get(extension)
        if highlight is None:
            highlight = (
                color_scheme.file_executable if shutil.which(self.abspath) is not None else
                color_scheme.file_link if self.path.is_symlink() else
                color_scheme.file_dir if self.path.is_dir() else
                color_scheme.file_file)
        return highlight

    def _formatted_metadata(self):
        return [
            self._mode_string(),
            '{:8s}'.format(username(self.uid)),
            '{:8s}'.format(groupname(self.gid)),
            '{:12}'.format(self.size),
            self.abspath]

    @staticmethod
    def _rwx(m):
        buffer = [
            'r' if (m & 0o4) != 0 else '-',
            'w' if (m & 0o2) != 0 else '-',
            'x' if (m & 0o1) != 0 else '-'
        ]
        return ''.join(buffer)
