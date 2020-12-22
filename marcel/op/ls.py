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

import pathlib
import stat

import marcel.object.error
import marcel.object.file
import marcel.op.filenamesop

File = marcel.object.file.File

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


class LsArgsParser(marcel.op.filenamesop.FilenamesOpArgsParser):

    def __init__(self, env):
        super().__init__('ls', env)
        self.add_flag_no_value('file', '-f', '--file')
        self.add_flag_no_value('dir', '-d', '--dir')
        self.add_flag_no_value('symlink', '-s', '--symlink')
        self.validate()


class Ls(marcel.op.filenamesop.FilenamesOp):

    def __init__(self, env):
        super().__init__(env, Ls.send_path)

    def __repr__(self):
        if self.d0:
            depth = '0'
        elif self.d1:
            depth = '1'
        else:
            depth = 'recursive'
        buffer = [f'depth={depth}']
        include = ''
        if self.file:
            include += 'f'
        if self.dir:
            include += 'd'
        if self.symlink:
            include += 's'
        if len(include) > 0:
            buffer.append(f'include={include}')
        if self.filenames:
            buffer.extend(self.filenames)
        args = ','.join(buffer)
        return f'ls({args})'

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    @staticmethod
    def send_path(op, file):
        assert type(file) is File, f'{type(file)} {file}'
        mode = file.path.lstat().st_mode
        s = stat.S_ISLNK(mode)
        f = stat.S_ISREG(mode) and not s
        d = stat.S_ISDIR(mode) and not s
        if ((op.file and f) or (op.dir and d) or (op.symlink and s)) and file.path not in op.emitted:
            try:
                op.send(file)
            except ValueError as e:
                import marcel.util
                marcel.util.print_stack()
                message = (f'Caught {e.__class__.__name__} on file with '
                           f'device = {file.device} and '
                           f'inode = {file.inode}, '
                           f'(file name may not be printable).')
                op.non_fatal_error(None, message)
            op.emitted.add(file.path)
