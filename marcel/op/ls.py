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

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.error
import marcel.object.file
import marcel.op.filenames


SUMMARY = '''
The specified files, directories, and symlinks are written to the output stream.
'''


DETAILS = '''
Generates a stream of {n:File} objects, representing files, directories and symlinks.

The flags {r:-0}, {r:-1}, and {r:-r} are mutually exclusive. {r:-1} is the default.

Flags {r:-f}, {r:-d}, and {r:-s} may be combined. If none of these flags are specified, then files, directories
and symlinks are all listed.

If no {r:filename}s are provided, then the currentn directory is listed.

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


class Ls(marcel.op.filenames.FilenamesOp):

    def __init__(self, env):
        super().__init__(env, op_has_target=False)
        self.d0 = False
        self.d1 = False
        self.dr = False
        self.file = False
        self.dir = False
        self.symlink = False
        self.base = None
        self.emitted = None

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

    # BaseOp

    def setup_1(self):
        super().setup_1()
        self.emitted = set()
        if len(self.roots) == 0:
            self.roots = [self.current_dir]
        if not (self.d0 or self.d1 or self.dr):
            self.d1 = True
        if not (self.file or self.dir or self.symlink):
            self.file = True
            self.dir = True
            self.symlink = True
        if len(self.roots) == 1:
            root = self.roots[0]
            self.base = root if root.is_dir() else root.parent
        else:
            self.base = None
            self.roots = sorted(self.roots)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # FilenamesOp

    def action(self, source):
        self.visit(source, 0)

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
            file = marcel.object.file.File(path, self.base)
            self.send(file)
            self.emitted.add(path)
