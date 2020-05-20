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

import collections.abc
import grp
import io
import pathlib
import dill
import pwd
import shutil
import subprocess
import sys
import time
import traceback


def username(uid):
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def uid(username):
    for entry in pwd.getpwall():
        if entry.pw_name == username:
            return entry.pw_uid
    return None


def groupname(gid):
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)


def gid(groupname):
    for entry in grp.getgrall():
        if entry.gr_name == groupname:
            return entry.gr_gid
    return None


def is_sequence(x):
    return isinstance(x, collections.abc.Sequence)


def is_sequence_except_string(x):
    return isinstance(x, collections.abc.Sequence) and not isinstance(x, str)


def is_generator(x):
    return isinstance(x, collections.abc.Generator)


def is_file(x):
    # Why not isinstance: Importing marcel.object.file.File results in circular imports
    return x.__class__.__name__ == 'File'


def is_executable(x):
    return shutil.which(x) is not None


def normalize_op_input(x):
    return (None if x is None else
            tuple(x) if is_sequence_except_string(x) else
            (x,))


def normalize_path(x):
    x = pathlib.Path(x)
    if x.as_posix().startswith('~'):
        x = x.expanduser()
    return x


def copy(x):
    try:
        buffer = io.BytesIO()
        pickler = dill.Pickler(buffer)
        pickler.dump(x)
        buffer.seek(0)
        unpickler = dill.Unpickler(buffer)
        return unpickler.load()
    except Exception as e:
        sys.stdout.flush()
        print(f'Cloning error: ({type(e)}) {e}', file=sys.__stderr__, flush=True)


def print_stack(file=None):
    if file is None:
        file = sys.__stderr__
    exception_type, exception, trace = sys.exc_info()
    print(f'Caught {exception_type}: {exception}', file=file)
    traceback.print_tb(trace, file=file)


def colorize(s, color):
    if color is None:
        return s
    # Those /001 and /002 codes seem to fix bug 2.
    # https://stackoverflow.com/questions/9468435/how-to-fix-column-calculation-in-python-readline-if-using-color-prompt
    bold = color.bold()
    italic = color.italic()
    style = ('\033[1m\033[3m' if bold and italic else
             '\033[1m' if bold else
             '\033[3m' if italic else
             '\033[0m')
    return (s
            if color is None else
            '\001{}\002\001\033[38;5;{}m\002{}\001\033[0m\002'.format(
                style,
                color.code,
                s))


def console_width():
    process = subprocess.Popen('stty size',
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL,
                               universal_newlines=True)
    process.wait()
    stdout, _ = process.communicate()
    try:
        console_columns = int(stdout.split()[1])
    except Exception:
        # Not running in a console.
        console_columns = None
    return console_columns


# Utility to print to stderr, flushing stdout first, to minimize weird ordering due to buffering.
def print_to_stderr(s):
    sys.stdout.flush()
    print(s, file=sys.stderr, flush=True)


class Stack:

    def __init__(self):
        self.contents = []

    def push(self, x):
        self.contents.append(x)

    def top(self):
        return self.contents[-1]

    def pop(self):
        return self.contents.pop()

    def is_empty(self):
        return len(self.contents) == 0

    def size(self):
        return len(self.contents)


class Trace:

    def __init__(self, tracefile):
        self.path = pathlib.Path(tracefile)
        self.path.touch(mode=0o666, exist_ok=True)
        self.path.unlink()
        self.file = self.path.open(mode='w')

    def write(self, line):
        print(f'{time.time()}: {line}', file=self.file, flush=True)

    def close(self):
        self.file.close()
