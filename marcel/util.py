# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option
# ) any later version.
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
import os
import pathlib
import pwd
import shlex
import shutil
import subprocess
import sys
import time
import traceback

import dill

from marcel.stringliteral import StringLiteral


def python_version():
    return sys.version_info.major, sys.version_info.minor


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
    t = type(x)
    return t is tuple or t is list


def is_generator(x):
    return hasattr(x, '__next__')


def is_file(x):
    # Why not isinstance: Importing marcel.object.file.File results in circular imports
    return x.__class__.__name__ == 'File'


def is_executable(x):
    return shutil.which(x) is not None


def wrap_op_input(x):
    t = type(x)
    return (None if x is None else
            x if t is tuple or t is list else
            (x,))


def unwrap_op_output(x):
    t = type(x)
    return (None if x is None else
            x[0] if (t is tuple or t is list) and len(x) == 1 else
            x)


# Generate a list of filenames, suitable for use on a bash command line, (i.e., quoted to handle tricky cases
# such as file names containing whitespace).
def quote_files(*files):
    def quote_file(file):
        if isinstance(file, pathlib.Path) or is_file(file):
            file = file.as_posix()
        return shlex.quote(file)
    return ' '.join((quote_file(file) for file in files))


def normalize_path(x):
    x = pathlib.Path(x)
    if x.as_posix().startswith('~'):
        x = x.expanduser()
    return x


def copy(x):
    try:
        return dill.loads(dill.dumps(x))
    except Exception as e:
        sys.stdout.flush()
        print(f'Cloning error on {type(x)}: ({type(e)}) {e}', file=sys.__stderr__, flush=True)
        print_stack_of_current_exception(sys.__stderr__)


def print_stack_of_current_exception(file=None):
    if file is None:
        file = sys.__stderr__
    exception_type, exception, trace = sys.exc_info()
    print(f'Caught {exception_type}: {exception}', file=file)
    traceback.print_tb(trace, file=file)
    file.flush()


def print_stack(file=None):
    if file is None:
        file = sys.__stderr__
    for line in traceback.format_stack()[:-2]:
        print(line.strip(), file=file)


def colorize(s, color):
    if color is None:
        return s
    bold = color.bold()
    italic = color.italic()
    style = ('\033[1m\033[3m' if bold and italic else
             '\033[1m' if bold else
             '\033[3m' if italic else
             '\033[0m')
    return f'{style}\033[38;5;{color.code}m{s}\033[0m'


def console_width():
    process = subprocess.run('stty size', shell=True, capture_output=True)
    console_columns = int(process.stdout.split()[1])
    return console_columns


# Utility to print to stderr, flushing stdout first, to minimize weird ordering due to buffering.
def print_to_stderr(env, message):
    sys.stdout.flush()
    if env and env.color_scheme():
        message = colorize(message, env.color_scheme().error)
    print(message, file=sys.stderr, flush=True)


def namespace_description(namespace):
    buffer = []
    for k, v in namespace.items():
        if k != '__builtins__':
            buffer.append(f'{k}: {v}')
    vars = '\n'.join(buffer)
    return f'{id(namespace)}\n{vars}'


def time_sec(f, *args, **kwargs):
    start = time.time()
    output = f(*args, **kwargs)
    stop = time.time()
    return stop - start, output


def iterable(x):
    return isinstance(x, collections.abc.Iterable)


def open_file(path, mode, exception_class):
    try:
        return open(path, mode)
    # FileNotFoundError should not occur. Missing files handled by FilenamesOp.
    except (IsADirectoryError, FileExistsError, PermissionError) as e:
        raise exception_class(f'Unable to open {path} with mode {mode}: {str(e)}')


def bash_executable():
    return shutil.which('bash')


def process_exists(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception as e:
        assert False, e


def accessible(dir):
    current_dir = os.getcwd()
    accessible = True
    try:
        os.chdir(dir)
    except PermissionError:
        accessible = False
    finally:
        os.chdir(current_dir)
        return accessible

def unescape(x):
    if x is None:
        return None
    if '\\' in x:
        unescaped = ''
        i = 0
        n = len(x)
        while i < n:
            c = x[i]
            i += 1
            if c == '\\':
                if i < n:
                    c = x[i]
                    i += 1
                    unescaped += c
            else:
                unescaped += c
    else:
        unescaped = x
    return unescaped

def one_of(x, types):
    for t in types:
        if isinstance(x, t):
            return True
    return False


def string_value(x):
    if x is None:
        return None
    assert isinstance(x, str)
    if type(x) is StringLiteral:
        x = x.value()
    return x



class Trace:

    def __init__(self, tracefile, replace=False):
        self.path = pathlib.Path(tracefile)
        if replace:
            self.path.unlink(missing_ok=True)
        self.path.touch(exist_ok=True)
        self.path.chmod(0o0666)

    def write(self, line):
        with self.path.open(mode='a') as file:
            print(f'{os.getpid()}: {line}', file=file, flush=True)

    # Caller is responsible for closing, e.g. with TRACE.open(...) as file ...
    def open(self):
        return self.path.open(mode='a')
