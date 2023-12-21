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
import importlib
import pathlib
import socket
import sys

import marcel.builtin
import marcel.compilable
import marcel.core
import marcel.directorystate
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
import marcel.object.workspace

Compilable = marcel.compilable.Compilable

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


class VarHandlerStartup(object):
    
    def __init__(self, env, startup_var_handler=None):
        self.env = env
        # Immutability isn't enforced by this var hander. But the set is populated during startup,
        # before VarHandler, which enforces immutability, is in place. Similarly, startup vars are discovered
        # during startup (duh!) and then transferred to VarHandler for use during post-startup operation.
        if startup_var_handler:
            self.immutable_vars = startup_var_handler.immutable_vars
            self.startup_vars = startup_var_handler.startup_vars
            self.save_vars = startup_var_handler.save_vars
        else:
            self.immutable_vars = set()
            self.startup_vars = None
            self.save_vars = set()
        self.vars_read = set()
        self.vars_written = set()
        self.vars_deleted = set()

    def hasvar(self, var):
        return var in self.env.namespace

    def getvar(self, var):
        assert var is not None
        try:
            value = self.env.namespace[var]
            self.vars_read.add(var)
            if isinstance(value, marcel.compilable.Compilable):
                value = value.value()
        except KeyError:
            value = None
        return value

    def setvar(self, var, value, save=True):
        assert var is not None
        current_value = self.env.namespace.get(var, None)
        self.vars_written.add(var)
        if type(current_value) is marcel.reservoir.Reservoir and value != current_value:
            current_value.ensure_deleted()
        if save:
            self.save_vars.add(var)
        self.env.namespace[var] = value

    def delvar(self, var):
        assert var is not None
        self.vars_deleted.add(var)
        self.save_vars.remove(var)
        return self.env.namespace.pop(var)

    def vars(self):
        return self.env.namespace

    def add_immutable_vars(self, *vars):
        self.immutable_vars.update(vars)

    def add_startup_vars(self, *vars):
        self.immutable_vars.update(vars)
        self.startup_vars = vars

    def add_save_vars(self, *vars):
        self.save_vars.update(vars)

    def add_changed_var(self, var):
        self.vars_written.add(var)

    def changes(self):
        changes = {}
        for var in self.vars_written:
            changes[var] = self.env.namespace[var]
        return changes

    def clear_changes(self):
        self.vars_read.clear()
        self.vars_written.clear()
        self.vars_deleted.clear()

    # Returns (var, value), where type(value) is Reservoir.
    def reservoirs(self):
        reservoirs = []
        for var in self.save_vars:
            value = self.getvar(var)
            if type(value) is marcel.reservoir.Reservoir:
                reservoirs.append((var, value))
        return reservoirs


class VarHandler(VarHandlerStartup):
    
    def __init__(self, startup_var_handler):
        super().__init__(startup_var_handler.env, startup_var_handler)

    def setvar(self, var, value, save=True):
        self.check_mutability(var)
        super().setvar(var, value, save)

    def delvar(self, var):
        self.check_mutability(var)
        return super().delvar(var)

    def add_written(self, var):
        self.vars_written.add(var)

    def check_mutability(self, var):
        if var in self.immutable_vars:
            raise marcel.exception.KillCommandException(
                f'{var} was defined by marcel, or in your startup script, '
                f'so it cannot be modified or deleted programmatically. '
                f'Edit the startup script instead.')


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
        self.directory_state = None
        # Source of ops and arg parsers.
        self.op_modules = marcel.opmodule.import_op_modules()
        # Lax var handling for now. Check immutability after startup is complete.
        self.var_handler = VarHandlerStartup(self)
        self.var_handler.add_immutable_vars('MARCEL_VERSION', 'HOME', 'PWD', 'DIRS', 'USER', 'HOST')
        self.var_handler.add_save_vars('PWD', 'DIRS')

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
        self.dir_state().change_current_dir(self.getvar('PWD'))

    def dir_state(self):
        return self.directory_state

    # Vars that are not mutable even during startup. I.e., startup script can't modify them.
    def never_mutable(self):
        return {'MARCEL_VERSION', 'HOME', 'USER', 'HOST'}

    def enforce_var_immutability(self, startup_vars=None):
        if startup_vars:
            self.var_handler.add_startup_vars(*startup_vars)
        self.var_handler = VarHandler(self.var_handler)

    def hasvar(self, var):
        return self.var_handler.hasvar(var)

    def getvar(self, var):
        return self.var_handler.getvar(var)

    def setvar(self, var, value):
        self.var_handler.setvar(var, value)

    def delvar(self, var):
        return self.var_handler.delvar(var)

    def vars(self):
        return self.var_handler.vars()

    # Should only call this from the assign op, when assigning something that is compilable,
    # i.e., something with source.
    def setvar_with_source(self, var, value, source):
        if callable(value):
            value = Compilable.for_function(self, f'({source})', value)
        elif type(value) is marcel.core.PipelineExecutable:
            value = Compilable.for_pipeline(self, source, value)
        self.setvar(var, value)

    def reservoirs(self):
        return self.var_handler.reservoirs()

    def cluster(self, name):
        cluster = None
        if type(name) is str:
            x = self.getvar(name)
            if type(x) is marcel.object.cluster.Cluster:
                cluster = x
        return cluster

    def check_nesting(self):
        return Environment.CheckNestingNoop()

    def changes(self):
        return self.var_handler.changes()

    def clear_changes(self):
        self.var_handler.clear_changes()

    def set_function_globals(self, function):
        function.set_globals(self.namespace)

    def color_scheme(self):
        return None

    def is_interactive_executable(self, x):
        return False

    # 'script' or 'api'
    def marcel_usage(self):
        assert False


class EnvironmentAPI(Environment):

    # globals: From the module in which marcel.api is imported.
    def __init__(self, globals):
        super().__init__(globals)
        self.directory_state = marcel.directorystate.DirectoryState(self)

    def clear_changes(self):
        self.var_handler.clear_changes()

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

    # Script and interactive usage rely on the import op to do imports. We don't want to pickle these symbols
    # in the environment because there is no point in persisting them with a workspace, and the contents of
    # modules are sometimes not serializable. So the env will store Import objects which can be persisted,
    # and handle reimportation.
    class Import(object):

        def __init__(self, module_name, symbol=None, rename=None):
            self.module_name = module_name
            self.symbol = symbol
            self.rename = rename

        def __repr__(self):
            buffer = [f'import({self.module_name}']
            if self.symbol is not None:
                buffer.append(f' {self.symbol}')
            if self.rename is not None:
                buffer.append(f' as {self.rename}')
            buffer.append(')')
            return ''.join(buffer)

    def __init__(self, locations, workspace):
        super().__init__(marcel.nestednamespace.NestedNamespace())
        assert workspace is not None
        # Standard locations of files important to marcel: config, history
        self.locations = locations
        # Support for pos()
        self.current_op = None
        # Vars defined during startup
        self.startup_vars = None
        # Immutable vars
        self.var_handler.add_immutable_vars('pos')
        # Marcel used with a script does not manipulate workspaces, but it is convenient to
        # have workspace defined, for use with Locations.
        self.workspace = workspace
        # Symbols imported need special handling
        self.imports = []
        self.directory_state = marcel.directorystate.DirectoryState(self)

    # Don't pickle everything

    def initialize_namespace(self):
        super().initialize_namespace()
        self.namespace.update({
            'WORKSPACE': self.workspace.name,
            'PROMPT': [EnvironmentInteractive.DEFAULT_PROMPT],
            'PROMPT_CONTINUATION': [EnvironmentInteractive.DEFAULT_PROMPT_CONTINUATION],
            'BOLD': marcel.object.color.Color.BOLD,
            'ITALIC': marcel.object.color.Color.ITALIC,
            'COLOR_SCHEME': marcel.object.color.ColorScheme(),
            'Color': marcel.object.color.Color,
            'pos': lambda: self.current_op.pos()})
        for key, value in marcel.builtin.__dict__.items():
            if not key.startswith('_'):
                self.namespace[key] = value
        self.restore_persistent_state_from_workspace()
        self.dir_state().change_current_dir(self.getvar('PWD'))
        # Need to make sure default workspace exists. Timing is delicate, this needs to be done before
        # Main runs Environment.read_config(). We are now toward the end of Environment creation, for both
        # Interactive and Script usage. (API doesn't use workspaces.)
        marcel.object.workspace.Workspace.default().create(self, DEFAULT_CONFIG)

    # This is destructive. Should be called only as the current workspace is being closed, and this Environment
    # is being saved.
    def persistent_state(self):
        # Things to persist:
        # - vars mentioned in save_vars
        # - imports
        save = dict()
        save_vars = self.var_handler.save_vars
        compilable_vars = []
        for var, value in self.namespace.items():
            if var in save_vars:
                save[var] = value
                if isinstance(value, Compilable):
                    compilable_vars.append(var)
                    value.purge()
        # Now that we know what to save, remove the compilables. Otherwise, shutdown, which examines the environment,
        # and does getvars, will fail when getvar is applied to a Compilable.
        for var in compilable_vars:
            del self.namespace[var]
        return {'namespace': save,
                'imports': self.imports}

    def restore_persistent_state_from_workspace(self):
        self.workspace.open(self)
        if not self.workspace.is_default():
            persistent_state = self.workspace.persistent_state
            saved_vars = persistent_state['namespace']
            self.namespace.update(saved_vars)
            for var, value in saved_vars.items():
                if isinstance(value, Compilable):
                    value.recompile(self)
            self.var_handler.add_save_vars(*saved_vars)
            imports = persistent_state['imports']
            for i in imports:
                self.import_module(i.module_name, i.symbol, i.rename)

    def never_mutable(self):
        vars = set(super().never_mutable())
        vars.update({'MARCEL_VERSION', 'HOME', 'USER', 'HOST', 'WORKSPACE'})
        return vars

    def read_config(self):
        config_path = self.locations.config_file_path(self.workspace)
        if config_path.exists():
            with open(config_path) as config_file:
                config_source = config_file.read()
            # Execute the config file. Imported and newly-defined symbols go into locals, which
            # will then be added to self.namespace, for use in the execution of op functions.
            locals = dict()
            exec(config_source, self.namespace, locals)
            self.namespace.update(locals)

    def check_nesting(self):
        return EnvironmentScript.CheckNesting(self)

    def set_function_globals(self, function):
        function.set_globals(self.vars())

    def marcel_usage(self):
        return 'script'

    def mark_possibly_changed(self, var):
        self.var_handler.add_changed_var(var)

    def import_module(self, module_name, symbol=None, rename=None):
        self.imports.append(EnvironmentScript.Import(module_name, symbol, rename))
        # Exceptions handle by import op
        module = importlib.import_module(module_name)
        if symbol is None:
            self.var_handler.setvar(module_name, module, save=False)
        elif symbol == '*':
            for name, value in module.__dict__.items():
                if not name.startswith('_'):
                    self.var_handler.setvar(name, value, save=False)
        else:
            value = module.__dict__[symbol]
            name = rename if rename is not None else symbol
            self.var_handler.setvar(name, value, save=False)

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

    @staticmethod
    def create(locations, workspace):
        env = EnvironmentScript(locations, workspace)
        env.initialize_namespace()
        return env

    @staticmethod
    def is_immutable(x):
        return callable(x) or type(x) in (int, float, str, bool, tuple, marcel.core.PipelineExecutable)


class EnvironmentInteractive(EnvironmentScript):

    DEFAULT_PROMPT = f'M {marcel.version.VERSION} $ '
    DEFAULT_PROMPT_CONTINUATION = '+$    '

    def __init__(self, locations, workspace):
        super().__init__(locations, workspace)
        # Actual config path. Needed to reread config file in case of modification.
        self.config_path = None
        # Used during readline editing
        self.edited_command = None
        # readline wrapper
        self.reader = None
        #
        self.var_handler.add_immutable_vars('PROMPT',
                                            'PROMPT_CONTINUATION',
                                            'BOLD',
                                            'ITALIC',
                                            'COLOR_SCHEME',
                                            'Color')

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
            return EnvironmentInteractive.DEFAULT_PROMPT

    @staticmethod
    def create(locations, workspace):
        env = EnvironmentInteractive(locations, workspace)
        env.initialize_namespace()
        return env
