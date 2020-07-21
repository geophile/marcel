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
import pathlib
import socket
import sys

import marcel.core
import marcel.exception
import marcel.object.cluster
import marcel.object.db
import marcel.object.color
import marcel.object.file
import marcel.object.process
import marcel.opmodule
import marcel.util
import marcel.version


class DirectoryState:

    VARS = ('DIRS', 'PWD')

    def __init__(self, namespace):
        self.namespace = namespace

    def __repr__(self):
        buffer = []
        for name in DirectoryState.VARS:
            buffer.append(f'{name}: {self.namespace[name]}')
        return f'DirectoryState({", ".join(buffer)})'

    def pwd(self):
        return pathlib.Path(self.namespace['PWD'])

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = (self.pwd() / directory.expanduser()).resolve(False)  # False: due to bug 27
        try:
            if not new_dir.exists():
                raise marcel.exception.KillCommandException(
                    f'Cannot cd into {new_dir}. Directory does not exist.')
            new_dir = new_dir.as_posix()
            self.dir_stack()[-1] = new_dir
            self.namespace['PWD'] = new_dir
            # So that executables have the same view of the current directory.
            os.chdir(new_dir)
        except FileNotFoundError:
            # Fix for bug 27
            pass

    def pushd(self, directory):
        dir_stack = self.dir_stack()
        if directory is None:
            if len(dir_stack) > 1:
                dir_stack[-2:] = [dir_stack[-1], dir_stack[-2]]
        else:
            assert isinstance(directory, pathlib.Path)
            dir_stack.append(directory.resolve().as_posix())
        self.cd(pathlib.Path(dir_stack[-1]))

    def popd(self):
        dir_stack = self.dir_stack()
        if len(dir_stack) > 1:
            dir_stack.pop()
            self.cd(pathlib.Path(dir_stack[-1]))

    def reset_dir_stack(self):
        dir_stack = self.dir_stack()
        dir_stack.clear()
        dir_stack.append(self.pwd())

    def dirs(self):
        dirs = list(self.dir_stack())
        dirs.reverse()
        return dirs

    def dir_stack(self):
        return self.namespace['DIRS']


class Environment:

    CONFIG_FILENAME = '.marcel.py'
    DEFAULT_PROMPT = f'M-{marcel.version.VERSION} $ '
    DEFAULT_PROMPT_CONTINUATION = '+$    '

    def __init__(self, config_file, old_namespace):
        user = getpass.getuser()
        homedir = pathlib.Path.home().resolve()
        host = socket.gethostname()
        editor = os.getenv('EDITOR')
        try:
            current_dir = pathlib.Path.cwd().resolve()
        except FileNotFoundError:
            raise marcel.exception.KillShellException(
                'Current directory does not exist! cd somewhere else and try again.')
        self.namespace = {} if old_namespace is None else old_namespace
        self.namespace.update({
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
            'define_db': self.define_db,
            'define_remote': self.define_remote,
            'Color': marcel.object.color.Color,
            'File': marcel.object.file.File,
            'Process': marcel.object.process.Process,
            'read': '[map (f: f.readlines()) | expand]'
        })
        if editor:
            self.namespace['EDITOR'] = editor
        self.clusters = {}
        self.dbs = {}
        self.config_path = self.read_config(config_file)
        self.directory_state = DirectoryState(self.namespace)
        # TODO: This is a hack. Clean it up once the env handles command history
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
        marcel.opmodule.import_op_modules(self)  # Sets self.op_modules

    def getvar(self, var):
        # If a var's value is obtained, and it contains mutable state (like a list), then
        # we have to allow for the possibility that the var changed.
        value = self.namespace.get(var, None)
        if self.modified_vars is not None and not Environment.immutable(value):
            self.modified_vars.add(var)
        return value

    def setvar(self, var, value):
        if self.modified_vars:
            self.modified_vars.add(var)
        self.namespace[var] = value

    def vars(self):
        return self.namespace

    def clear_changes(self):
        self.modified_vars = set()

    def changes(self):
        changes = {}
        for var in self.modified_vars:
            changes[var] = self.namespace[var]
        return changes

    def prompts(self):
        return (self.prompt_string(self.getvar('PROMPT')),
                self.prompt_string(self.getvar('PROMPT_CONTINUATION')))

    def define_remote(self, name, user, identity, host=None, hosts=None):
        self.clusters[name] = marcel.object.cluster.define_remote(name, user, identity, host, hosts)

    def remote(self, name):
        return self.clusters.get(name, None)

    def define_db(self, name, driver, dbname, user, password=None, host=None, port=None):
        self.dbs[name] = marcel.object.db.define_db(name, driver, dbname, user, password, host, port)

    def db(self, name):
        return self.dbs.get(name, None)

    def dir_state(self):
        return self.directory_state

    def color_scheme(self):
        return self.getvar('COLOR_SCHEME')

    def set_color_scheme(self, color_scheme):
        self.setvar('COLOR_SCHEME', color_scheme)

    def read_config(self, config_path):
        config_path = (pathlib.Path(config_path)
                       if config_path else
                       pathlib.Path.home() / Environment.CONFIG_FILENAME).expanduser()
        if config_path.exists():
            with open(config_path.as_posix()) as config_file:
                config_source = config_file.read()
            locals = {}
            # Execute the config file. Imported and newly-defined symbols go into locals, which
            # will then be added to self.namespace, for use in the execution of op functions.
            exec(config_source, self.namespace, locals)
            self.namespace.update(locals)
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
                    buffer.append(marcel.util.colorize(x, color) if color else x)
            return ''.join(buffer)
        except Exception as e:
            print(f'Bad prompt definition in {prompt_pieces}: {e}', file=sys.stderr)
            return Environment.DEFAULT_PROMPT

    @staticmethod
    def immutable(x):
        return callable(x) or type(x) in (int, float, str, bool, tuple, marcel.core.Pipeline)

