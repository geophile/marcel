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
import shutil
import socket
import sys

import marcel.builtin
import marcel.core
import marcel.exception
import marcel.function
import marcel.locations
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

    def __init__(self, env):
        self.env = env

    def __repr__(self):
        return f'DirectoryState({self._dir_stack()})'

    def pwd(self):
        # return pathlib.Path(self.env.getvar('PWD'))
        return pathlib.Path(os.getcwd())

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = (self.pwd() / directory.expanduser()).resolve(False)  # False: due to bug 27
        new_dir = new_dir.as_posix()
        # So that executables have the same view of the current directory.
        os.chdir(new_dir)
        self._dir_stack()[-1] = new_dir
        self.env.namespace['PWD'] = new_dir

    def pushd(self, directory):
        self._clean_dir_stack()
        # Operate on a copy of the directory stack. Don't want to change the
        # actual stack until the cd succeeds (bug 133).
        dir_stack = list(self._dir_stack())
        if directory is None:
            if len(dir_stack) > 1:
                dir_stack[-2:] = [dir_stack[-1], dir_stack[-2]]
        else:
            assert isinstance(directory, pathlib.Path)
            dir_stack.append(directory.resolve().as_posix())
        self.cd(pathlib.Path(dir_stack[-1]))
        self.env.namespace['DIRS'] = dir_stack

    def popd(self):
        self._clean_dir_stack()
        dir_stack = self._dir_stack()
        if len(dir_stack) > 1:
            self.cd(pathlib.Path(dir_stack[-2]))
            dir_stack.pop()

    def reset_dir_stack(self):
        dir_stack = self._dir_stack()
        dir_stack.clear()
        dir_stack.append(self.pwd())

    def dirs(self):
        self._clean_dir_stack()
        dirs = list(self._dir_stack())
        dirs.reverse()
        return dirs

    def _dir_stack(self):
        return self.env.getvar('DIRS')

    # Remove entries that are not files, and not accessible, (presumably due to changes since they entered the stack).
    def _clean_dir_stack(self):
        clean = []
        removed = []
        dirs = self._dir_stack()
        for dir in dirs:
            if os.path.exists(dir) and os.access(dir, mode=os.X_OK, follow_symlinks=True):
                clean.append(dir)
            else:
                removed.append(dir)
        if len(clean) < len(dirs):
            self.env.namespace['DIRS'] = clean
            buffer = ['The following directories have been removed from the directory stack because',
                      'they are no longer accessible:']
            buffer.extend(removed)
            raise marcel.exception.KillCommandException('\n'.join(buffer))


class Environment(object):

    class CheckNestingNoop(object):

        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def __init__(self, namespace):
        # Where environment variables live.
        self.namespace = namespace
        # Directory stack, including current directory.
        self.directory_state = DirectoryState(self)
        # Source of ops and arg parsers.
        self.op_modules = marcel.opmodule.import_op_modules()
        # Variables defined in startup script are immutable. Also, vars representing state of host OS.
        self.immutable = set()
        # Where to find bash.
        self.bash = shutil.which('bash')

    def initialize_namespace(self):
        try:
            homedir = pathlib.Path.home().resolve().as_posix()
        except FileNotFoundError:
            raise marcel.exception.KillShellException(
                'Home directory does not exist!')
        try:
            current_dir = pathlib.Path.cwd().resolve().as_posix()
        except FileNotFoundError:
            raise marcel.exception.KillShellException(
                'Current directory does not exist! cd somewhere else and try again.')
        self.namespace.update({
            'MARCEL_VERSION': marcel.version.VERSION,
            'HOME': homedir,
            'PWD': current_dir,
            'DIRS': [current_dir],
            'USER': getpass.getuser(),
            'HOST': socket.gethostname()
        })
        self.immutable.update([
            'HOME',
            'PWD',
            'DIRS',
            'USER',
            'HOST',
            'MARCEL_VERSION'
        ])

    def hasvar(self, var):
        return var in self.namespace

    def getvar(self, var):
        assert var is not None
        try:
            value = self.namespace[var]
        except KeyError:
            value = None
        return value

    def setvar(self, var, value):
        assert var is not None
        self.check_mutable(var)
        current_value = self.namespace.get(var, None)
        if type(current_value) is marcel.reservoir.Reservoir:
            current_value.ensure_deleted()
        self.namespace[var] = value

    def delvar(self, var):
        assert var is not None
        self.check_mutable(var)
        return self.namespace.pop(var)

    def vars(self):
        return self.namespace

    def dir_state(self):
        return self.directory_state

    def cluster(self, name):
        cluster = None
        if type(name) is str:
            x = self.getvar(name)
            if type(x) is marcel.object.cluster.Cluster:
                cluster = x
        return cluster

    def check_nesting(self):
        return Environment.CheckNestingNoop()

    def clear_changes(self):
        pass

    def set_function_globals(self, function):
        function.set_globals(self.namespace)

    def color_scheme(self):
        return None

    def check_mutable(self, var):
        if var in self.immutable:
            raise marcel.exception.KillCommandException(
                f'{var} was defined by marcel, or in your startup script, '
                f'so it cannot be modified or deleted programmatically. '
                f'Edit the startup script instead.')

    def is_interactive_executable(self, x):
        return False

    # 'script' or 'api'
    def marcel_usage(self):
        assert False

    @staticmethod
    def create():
        env = Environment(dict())
        env.initialize_namespace()
        return env


class EnvironmentAPI(Environment):

    # globals: From the module in which marcel.api is imported.
    def __init__(self, globals):
        super().__init__(globals)

    def changes(self):
        return None

    def clear_changes(self):
        pass

    def marcel_usage(self):
        return 'api'

    @staticmethod
    def create(globals):
        env = EnvironmentAPI(globals)
        env.initialize_namespace()
        return env


class EnvironmentScript(Environment):

    class CheckNesting(object):

        def __init__(self, env):
            self.env = env
            self.depth = None

        def __enter__(self):
            self.depth = self.env.vars().n_scopes()

        def __exit__(self, exc_type, exc_val, exc_tb):
            assert self.env.vars().n_scopes() == self.depth, self.env.vars().n_scopes()
            self.depth = None

    class NoMutabilityCheck(object):

        def __init__(self, env):
            self.env = env
            self.immutable = env.immutable

        def __enter__(self):
            self.env.immutable = set()

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.env.immutable = self.immutable

    def __init__(self):
        super().__init__(marcel.nestednamespace.NestedNamespace())
        # Standard locations of files important to marcel: config, history
        self.locations = marcel.locations.Locations(self)
        # Actual config path. Needed to reread config file in case of modification.
        self.config_path = None
        # For tracking env var changes made by job
        self.modified_vars = set()
        # Support for pos()
        self.current_op = None
        #
        self.initialize_namespace()

    # Don't pickle everything

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['op_modules']
        del state['immutable']
        del state['bash']
        del state['locations']
        del state['config_path']
        del state['modified_vars']
        del state['current_op']
        return state

    def initialize_namespace(self):
        super().initialize_namespace()
        self.namespace.update({'pos': lambda: self.current_op.pos()})
        for key, value in marcel.builtin.__dict__.items():
            if not key.startswith('_'):
                self.namespace[key] = value
        self.immutable.update(['pos'])

    def read_config(self, config_path=None):
        config_path = (self.locations.config_file_path()
                       if config_path is None else
                       pathlib.Path(config_path))
        if not config_path.exists():
            with open(config_path, 'w') as config_file:
                config_file.write(DEFAULT_CONFIG)
            config_path.chmod(0o600)
        with open(config_path) as config_file:
            config_source = config_file.read()
        locals = {}
        # Execute the config file. Imported and newly-defined symbols go into locals, which
        # will then be added to self.namespace, for use in the execution of op functions.
        exec(config_source, self.namespace, locals)
        self.namespace.update(locals)
        self.immutable.update(locals.keys())
        self.config_path = config_path

    def check_nesting(self):
        return EnvironmentScript.CheckNesting(self)

    def set_function_globals(self, function):
        function.set_globals(self.vars())

    def getvar(self, var):
        value = super().getvar(var)
        if var in self.namespace:
            self.note_var_access(var, value)
        return value

    def setvar(self, var, value):
        super().setvar(var, value)
        return self.modified_vars.add(var)

    def clear_changes(self):
        self.modified_vars = set()

    def changes(self):
        changes = {}
        for var in self.modified_vars:
            changes[var] = self.namespace[var]
        return changes

    def marcel_usage(self):
        return 'script'

    def mark_possibly_changed(self, var):
        if self.modified_vars is not None and var is not None:
            self.modified_vars.add(var)

    def db(self, name):
        db = None
        x = self.getvar(name)
        if type(x) is marcel.object.db.Database:
            db = x
        return db

    def color_scheme(self):
        return self.getvar('COLOR_SCHEME')

    def set_color_scheme(self, color_scheme):
        self.setvar('COLOR_SCHEME', color_scheme)

    def is_interactive_executable(self, x):
        interactive_executables = self.getvar('INTERACTIVE_EXECUTABLES')
        return (interactive_executables is not None and
                type(interactive_executables) in (tuple, list) and
                x in interactive_executables)

    def note_var_access(self, var, value):
        if not EnvironmentScript.is_immutable(value):
            self.modified_vars.add(var)

    def no_mutability_check(self):
        return EnvironmentScript.NoMutabilityCheck(self)

    @staticmethod
    def create():
        env = EnvironmentScript()
        env.initialize_namespace()
        return env

    @staticmethod
    def is_immutable(x):
        return callable(x) or type(x) in (int, float, str, bool, tuple, marcel.core.PipelineExecutable)


class EnvironmentInteractive(EnvironmentScript):

    DEFAULT_PROMPT = f'M {marcel.version.VERSION} $ '
    DEFAULT_PROMPT_CONTINUATION = '+$    '

    def __init__(self):
        super().__init__()
        # Actual config path. Needed to reread config file in case of modification.
        self.config_path = None
        # Used during readline editing
        self.edited_command = None
        # readline wrapper
        self.reader = None
        # Workspace
        self.workspace = None
        #
        self.initialize_namespace()
    # Don't pickle everything

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['reader']
        del state['op_modules']
        del state['immutable']
        del state['bash']
        del state['locations']
        del state['config_path']
        del state['edited_command']
        del state['modified_vars']
        del state['current_op']
        return state

    def initialize_namespace(self):
        super().initialize_namespace()
        self.namespace.update({
            'PROMPT': [EnvironmentInteractive.DEFAULT_PROMPT],
            'PROMPT_CONTINUATION': [EnvironmentInteractive.DEFAULT_PROMPT_CONTINUATION],
            'BOLD': marcel.object.color.Color.BOLD,
            'ITALIC': marcel.object.color.Color.ITALIC,
            'COLOR_SCHEME': marcel.object.color.ColorScheme(),
            'Color': marcel.object.color.Color
        })
        editor = os.getenv('EDITOR')
        if editor:
            self.namespace['EDITOR'] = editor
        self.immutable.update([
            'PROMPT',
            'PROMPT_CONTINUATION',
            'BOLD',
            'ITALIC',
            'COLOR_SCHEME',
            'Color'])

    def prompts(self):
        return (self.prompt_string(self.getvar('PROMPT')),
                self.prompt_string(self.getvar('PROMPT_CONTINUATION')))

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
            return EnvironmentScript.DEFAULT_PROMPT

    @staticmethod
    def create():
        env = EnvironmentInteractive()
        env.initialize_namespace()
        return env
