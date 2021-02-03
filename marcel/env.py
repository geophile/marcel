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

import getpass
import os
import os.path
import pathlib
import socket
import sys

import marcel.builtin
import marcel.core
import marcel.exception
import marcel.function
import marcel.nestednamespace
import marcel.object.cluster
import marcel.object.db
import marcel.object.color
import marcel.object.file
import marcel.object.process
import marcel.opmodule
import marcel.reservoir
import marcel.util
import marcel.version

DEFAULT_CONFIG = '''from marcel.builtin import *

# COLOR_EXT_IMAGE = Color(3, 0, 2, BOLD)
# COLOR_EXT_SOURCE = Color(0, 3, 4, BOLD)
# 
# COLOR_SCHEME.file_file = Color(5, 5, 5, BOLD)
# COLOR_SCHEME.file_dir = Color(0, 2, 3, BOLD)
# COLOR_SCHEME.file_link = Color(4, 2, 0, BOLD)
# COLOR_SCHEME.file_executable = Color(0, 4, 0, BOLD)
# COLOR_SCHEME.file_extension = {
#     'jpg': COLOR_EXT_IMAGE,
#     'jpeg': COLOR_EXT_IMAGE,
#     'png': COLOR_EXT_IMAGE,
#     'mov': COLOR_EXT_IMAGE,
#     'avi': COLOR_EXT_IMAGE,
#     'gif': COLOR_EXT_IMAGE,
#     'py': COLOR_EXT_SOURCE,
#     'c': COLOR_EXT_SOURCE,
#     'c++': COLOR_EXT_SOURCE,
#     'cpp': COLOR_EXT_SOURCE,
#     'cxx': COLOR_EXT_SOURCE,
#     'h': COLOR_EXT_SOURCE,
#     'java': COLOR_EXT_SOURCE,
#     'php': COLOR_EXT_SOURCE
# }
# COLOR_SCHEME.error = Color(5, 5, 0)
# COLOR_SCHEME.process_pid = Color(0, 3, 5, BOLD)
# COLOR_SCHEME.process_ppid = Color(0, 2, 4, BOLD)
# COLOR_SCHEME.process_status = Color(3, 1, 0, BOLD)
# COLOR_SCHEME.process_user = Color(0, 2, 2, BOLD)
# COLOR_SCHEME.process_command = Color(3, 2, 0, BOLD)
# COLOR_SCHEME.help_reference = Color(5, 3, 0)
# COLOR_SCHEME.help_bold = Color(5, 4, 1, BOLD)
# COLOR_SCHEME.help_italic = Color(5, 5, 2, ITALIC)
# COLOR_SCHEME.help_name = Color(4, 1, 0)
# COLOR_SCHEME.history_id = Color(0, 3, 5, BOLD)
# COLOR_SCHEME.history_command = Color(4, 3, 0, BOLD)
# COLOR_SCHEME.color_scheme_key = Color(2, 4, 0)
# COLOR_SCHEME.color_scheme_value = Color(0, 3, 4)

PROMPT = [lambda: PWD, ' $ ']
PROMPT_CONTINUATION = [lambda: PWD, ' + ']

INTERACTIVE_EXECUTABLES = [
    'emacs',
    'less',
    'man',
    'more',
    'psql',
    'top',
    'vi',
    'vim'
]
'''


class DirectoryState:
    VARS = ('DIRS', 'PWD')

    def __init__(self, env):
        self.env = env

    def __repr__(self):
        buffer = []
        for name in DirectoryState.VARS:
            buffer.append(f'{name}: {self.env.getvar(name)}')
        return f'DirectoryState({", ".join(buffer)})'

    def pwd(self):
        return pathlib.Path(self.env.getvar('PWD'))

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = (self.pwd() / directory.expanduser()).resolve(False)  # False: due to bug 27
        new_dir = new_dir.as_posix()
        # So that executables have the same view of the current directory.
        os.chdir(new_dir)
        self.dir_stack()[-1] = new_dir
        self.env.setvar('PWD', new_dir)

    def pushd(self, directory):
        self.clean_dir_stack()
        # Operate on a copy of the directory stack. Don't want to change the
        # actual stack until the cd succeeds (bug 133).
        dir_stack = list(self.dir_stack())
        if directory is None:
            if len(dir_stack) > 1:
                dir_stack[-2:] = [dir_stack[-1], dir_stack[-2]]
        else:
            assert isinstance(directory, pathlib.Path)
            dir_stack.append(directory.resolve().as_posix())
        self.cd(pathlib.Path(dir_stack[-1]))
        self.env.setvar('DIRS', dir_stack)

    def popd(self):
        self.clean_dir_stack()
        dir_stack = self.dir_stack()
        if len(dir_stack) > 1:
            self.cd(pathlib.Path(dir_stack[-2]))
            dir_stack.pop()

    def reset_dir_stack(self):
        dir_stack = self.dir_stack()
        dir_stack.clear()
        dir_stack.append(self.pwd())

    def dirs(self):
        self.clean_dir_stack()
        dirs = list(self.dir_stack())
        dirs.reverse()
        return dirs

    def dir_stack(self):
        return self.env.getvar('DIRS')

    # Remove entries that are not files, and not accessible, (presumably due to changes since they entered the stack).
    def clean_dir_stack(self):
        clean = []
        removed = []
        dirs = self.dir_stack()
        for dir in dirs:
            if os.path.exists(dir) and os.access(dir, mode=os.X_OK, follow_symlinks=True):
                clean.append(dir)
            else:
                removed.append(dir)
        if len(clean) < len(dirs):
            self.env.setvar('DIRS', clean)
            buffer = ['The following directories have been removed from the directory stack because',
                      'they are no longer accessible:']
            buffer.extend(removed)
            raise marcel.exception.KillCommandException('\n'.join(buffer))


class Environment:
    CONFIG_FILENAME = '.marcel.py'
    DEFAULT_PROMPT = f'M-{marcel.version.VERSION} $ '
    DEFAULT_PROMPT_CONTINUATION = '+$    '

    @staticmethod
    def new(config_file, old_namespace):
        env = Environment()
        user = getpass.getuser()
        homedir = pathlib.Path.home().resolve()
        host = socket.gethostname()
        editor = os.getenv('EDITOR')
        try:
            current_dir = pathlib.Path.cwd().resolve()
        except FileNotFoundError:
            raise marcel.exception.KillShellException(
                'Current directory does not exist! cd somewhere else and try again.')
        env.current_op = None
        initial_namespace = os.environ.copy() if old_namespace is None else old_namespace
        initial_namespace.update({
            'USER': user,
            'HOME': homedir.as_posix(),
            'HOST': host,
            'MARCEL_VERSION': marcel.version.VERSION,
            'PWD': current_dir.as_posix(),
            'DIRS': [current_dir.as_posix()],
            'PROMPT': [Environment.DEFAULT_PROMPT],
            'PROMPT_CONTINUATION': [Environment.DEFAULT_PROMPT_CONTINUATION],
            'BOLD': marcel.object.color.Color.BOLD,
            'ITALIC': marcel.object.color.Color.ITALIC,
            'COLOR_SCHEME': marcel.object.color.ColorScheme(),
            'Color': marcel.object.color.Color,
            # EXPERIMENT
            'pos': lambda: env.current_op.pos()
        })
        if editor:
            initial_namespace['EDITOR'] = editor
        for key, value in marcel.builtin.__dict__.items():
            if not key.startswith('_'):
                initial_namespace[key] = value
        env.namespace = marcel.nestednamespace.NestedNamespace(initial_namespace)
        env.builtin_symbols = set(env.namespace.keys())
        env.config_symbols = None  # Set by compute_config_symbols() after startup script is run
        env.config_path = env.read_config(config_file)
        env.directory_state = DirectoryState(env)
        # TODO: This is a hack. Clean it up once the env handles command history
        env.edited_command = None
        env.op_modules = None
        env.reader = None
        env.modified_vars = set()
        return env

    def __init__(self):
        self.namespace = None
        self.builtin_symbols = None
        self.config_symbols = None
        self.config_path = None
        self.directory_state = None
        self.edited_command = None
        self.op_modules = None
        self.reader = None
        self.modified_vars = None

    def __getstate__(self):
        return {'namespace': self.namespace,
                'directory_state': self.directory_state,
                'modified_vars': self.modified_vars}

    def __setstate__(self, state):
        self.__dict__.update(state)

    def hasvar(self, var):
        return var in self.namespace

    def getvar(self, var):
        assert var is not None
        try:
            value = self.namespace[var]
            self.note_var_access(var, value)
        except KeyError:
            value = None
        return value

    def setvar(self, var, value):
        assert var is not None
        current_value = self.namespace.get(var, None)
        if type(current_value) is marcel.reservoir.Reservoir:
            current_value.ensure_deleted()
        self.namespace[var] = value
        self.modified_vars.add(var)

    def delvar(self, var):
        assert var is not None
        value = self.namespace.pop(var, None)
        if type(value) is marcel.reservoir.Reservoir:
            value.ensure_deleted()

    def vars(self):
        return self.namespace

    def clear_changes(self):
        self.modified_vars = set()

    def changes(self):
        changes = {}
        for var in self.modified_vars:
            changes[var] = self.namespace[var]
        return changes

    def mark_possibly_changed(self, var):
        if self.modified_vars is not None and var is not None:
            self.modified_vars.add(var)

    def prompts(self):
        return (self.prompt_string(self.getvar('PROMPT')),
                self.prompt_string(self.getvar('PROMPT_CONTINUATION')))

    def cluster(self, name):
        cluster = None
        if type(name) is str:
            x = self.getvar(name)
            if type(x) is marcel.object.cluster.Cluster:
                cluster = x
        return cluster

    def db(self, name):
        db = None
        x = self.getvar(name)
        if type(x) is marcel.object.db.Database:
            db = x
        return db

    def dir_state(self):
        return self.directory_state

    def color_scheme(self):
        return self.getvar('COLOR_SCHEME')

    def set_color_scheme(self, color_scheme):
        self.setvar('COLOR_SCHEME', color_scheme)

    def is_interactive_executable(self, x):
        interactive_executables = self.getvar('INTERACTIVE_EXECUTABLES')
        return (interactive_executables is not None and
                type(interactive_executables) in (tuple, list) and
                x in interactive_executables)

    # Remove Reservoirs, which can be arbitrarily large.
    def remotify(self):
        # Shallow copy suffices, except for the namespace which must be modified.
        remote_env = marcel.util.copy(self)
        # remote_env = self.shallow_copy()
        # remote_env.namespace = remote_env.namespace.copy()
        for var, value in self.namespace.items():
            if type(value) is marcel.reservoir.Reservoir:
                del remote_env.namespace[var]
        return remote_env

    def read_config(self, config_path):
        config_path = (pathlib.Path(config_path)
                       if config_path else
                       pathlib.Path.home() / Environment.CONFIG_FILENAME).expanduser()
        if not config_path.exists():
            with open(config_path.as_posix(), 'w') as config_file:
                config_file.write(DEFAULT_CONFIG)
        with open(config_path.as_posix()) as config_file:
            config_source = config_file.read()
        locals = {}
        # Execute the config file. Imported and newly-defined symbols go into locals, which
        # will then be added to self.namespace, for use in the execution of op functions.
        exec(config_source, self.namespace, locals)
        self.namespace.update(locals)
        self.config_symbols = set(locals.keys())
        return config_path

    def prompt_string(self, prompt_pieces):
        try:
            buffer = []
            color = None
            for x in prompt_pieces:
                # In each iteration, we either have a color, or a prompt component. In the latter case,
                # append it to the buffer, colorizing if color is defined.
                if isinstance(x, marcel.object.color.Color):
                    color = x
                    x = None
                elif isinstance(x, str):
                    pass
                elif callable(x):
                    # Set up the namespace for calling the function
                    x.__globals__.update(self.namespace)
                    x = x()
                else:
                    raise marcel.exception.KillShellException(f'Invalid prompt component: {x}')
                if x:
                    x = str(x)
                    buffer.append(marcel.util.colorize(x, color, readline=True) if color else x)
            return ''.join(buffer)
        except Exception as e:
            print(f'Bad prompt definition in {prompt_pieces}: {e}', file=sys.stderr)
            return Environment.DEFAULT_PROMPT

    def note_var_access(self, var, value):
        if not Environment.immutable(value):
            self.modified_vars.add(var)

    def shallow_copy(self):
        copy = Environment()
        copy.__dict__.update(self.__dict__)
        return copy

    @staticmethod
    def immutable(x):
        return callable(x) or type(x) in (int, float, str, bool, tuple, marcel.core.Pipeline)
