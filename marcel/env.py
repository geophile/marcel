# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
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
import os
import pathlib
import socket
import sys

import marcel.builtin
import marcel.cliargs
import marcel.compilable
import marcel.core
import marcel.directorystate
import marcel.exception
import marcel.function
import marcel.locations
import marcel.object.cluster
import marcel.object.db
import marcel.object.color
import marcel.object.file
import marcel.object.process
import marcel.opmodule
import marcel.reservoir
import marcel.structish
import marcel.util
import marcel.version

Compilable = marcel.compilable.Compilable


class Environment(object):

    class CheckNestingNoop(object):

        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def __init__(self, workspace, trace):
        assert workspace is not None
        self.workspace = workspace
        self.locations = marcel.locations.Locations()
        # Directory stack, including current directory.
        self.directory_state = marcel.directorystate.DirectoryState(self)
        # Compilables need to be compiled in order of creation. (Locating them in namespace does not preserve order.)
        self.compilables = []  # list of var names
        # Source of ops and arg parsers.
        self.op_modules = marcel.opmodule.import_op_modules()
        # Lax var handling for now. Check immutability after startup is complete.
        self.trace = trace if trace else Trace()
        self.var_handler.add_immutable_vars('MARCEL_VERSION', 'HOME', 'PWD', 'DIRS', 'USER', 'HOST')
        self.var_handler.add_save_vars('PWD', 'DIRS')
        self.imports = set()

    # TODO: These properties are scaffolding during move of namespace to Workspace

    @property
    def namespace(self):
        return self.workspace.namespace

    @property
    def var_handler(self):
        return self.workspace.var_handler

    def initial_namespace(self):
        initial_namespace = dict()
        try:
            homedir = pathlib.Path.home().resolve().as_posix()
        except FileNotFoundError:
            raise marcel.exception.KillShellException(
                'Home directory does not exist!')
        try:
            current_dir = pathlib.Path.cwd().resolve().as_posix()
        except FileNotFoundError:
            current_dir = homedir
        initial_namespace.update({
            'MARCEL_VERSION': marcel.version.VERSION,
            'HOME': homedir,
            'PWD': current_dir,
            'DIRS': [current_dir],
            'USER': getpass.getuser(),
            'HOST': socket.gethostname(),
            'parse_args': lambda usage=None, **kwargs: marcel.cliargs.parse_args(self, usage, **kwargs)
        })
        return initial_namespace

    def dir_state(self):
        return self.directory_state

    def persistent_state(self):
        # Things to persist:
        # - vars mentioned in save_vars
        # - imports
        # - compilables
        save = dict()
        save_vars = self.var_handler.save_vars
        compilable_vars = []
        for var, value in self.workspace.namespace.items():
            if var in save_vars:
                save[var] = value
                if isinstance(value, Compilable):
                    compilable_vars.append(var)
                    value.purge()
        # Now that we know what to save, remove the compilables. Otherwise, shutdown, which examines the environment,
        # and does getvars, will fail when getvar is applied to a Compilable.
        for var in compilable_vars:
            del self.workspace.namespace[var]
        return {'namespace': save,
                'imports': self.imports,
                'compilables': self.compilables}

    def restore_persistent_state_from_workspace(self, workspace):
        persistent_state = workspace.persistent_state
        # Do the imports before compilation, which may depend on the imports.
        imports = persistent_state['imports']
        for i in imports:
            try:
                self.import_module(i.module_name, i.symbol, i.name)
            except marcel.exception.ImportException as e:
                print(f'Unable to import {i.module_name}: e.message', file=sys.stderr)
        # Restore vars.
        saved_vars = persistent_state['namespace']
        self.workspace.namespace.update(saved_vars)
        self.var_handler.add_save_vars(*saved_vars)
        # Recompile compilables. Tracking of compilables in persistent state is new as of 0.26.0, so
        # allow for them to be missing. (We are then subject to bug 254, which is why self.compilables
        # was introduced.)
        try:
            compilables = persistent_state['compilables']
        except KeyError:
            compilables = []
            for var, value in saved_vars.items():
                if isinstance(value, Compilable):
                    compilables.append(var)
        for var in compilables:
            # This assigns env to the var's value, which should be a compilable. This will allow compilation
            # to occur when needed.
            self.getvar(var)

    # Vars that are not mutable even during startup. I.e., startup script can't modify them.
    def never_mutable(self):
        return {'MARCEL_VERSION', 'HOME', 'USER', 'HOST'}

    def enforce_var_immutability(self, startup_vars=None):
        if startup_vars:
            self.var_handler.add_startup_vars(*startup_vars)
        self.var_handler.enforce_immutability(True)

    def hasvar(self, var):
        return self.var_handler.hasvar(var)

    def getvar(self, var):
        return self.var_handler.getvar(var)

    def setvar(self, var, value):
        self.var_handler.setvar(var, value)

    # Should only call this from the assign op, when assigning something that is compilable,
    # i.e., something with source.
    def setvar_with_source(self, var, value, source):
        if callable(value):
            value = Compilable.for_function(self, f'({source})', value)
            self.compilables.append(var)
        elif type(value) is marcel.core.PipelineExecutable:
            value = Compilable.for_pipeline(self, source, value)
            self.compilables.append(var)
        self.setvar(var, value)

    def delvar(self, var):
        return self.var_handler.delvar(var)

    def vars(self):
        return self.var_handler.vars()

    def reservoirs(self):
        return self.var_handler.reservoirs()

    def cluster(self, name):
        cluster = None
        if isinstance(name, str):
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
        function.set_globals(self.workspace.namespace)

    def color_scheme(self):
        return None

    def is_interactive_executable(self, x):
        return False

    # 'script' or 'api'
    def marcel_usage(self):
        assert False

    def api_usage(self):
        return self.marcel_usage() == 'api'

    def go_to_current_dir(self):
        # The directory named by PWD can disappear, and going to it will fail.
        # Use HOME as an alternative.
        current_dir = self.getvar('PWD')
        if current_dir:  # False for '',  None
            if not (os.path.exists(current_dir) and os.path.isdir(current_dir)):
                current_dir = None
        if not current_dir:
            current_dir = self.getvar('HOME')
        os.chdir(current_dir)
        self.dir_state().change_current_dir(current_dir)

    @classmethod
    def create(cls,
               workspace=None,
               globals=None,
               trace=None):
        # Don't use a default value for workspace. Default value expressions are evaluted
        # on import, which may be too early. Discovered this gotcha on a unit test. Unit tests
        # set HOME (in os.environ). But Workspace.default() creates a Locations object which
        # depends on HOME. So Locations were wrong because HOME had not yet been reset for the test.
        if workspace is None:
            import marcel.object.workspace
            workspace = marcel.object.workspace.Workspace.default()
        env = cls(workspace=workspace, trace=trace)
        initial_namespace = env.initial_namespace()
        workspace.open(env, initial_namespace)
        assert (cls is EnvironmentAPI) == (globals is not None)
        if globals is not None:
            workspace.namespace.update(globals)
        return env


class EnvironmentAPI(Environment):

    # globals: From the module in which marcel.api is imported.
    def __init__(self, workspace=None, trace=None):
        workspace = Workspace.default() if workspace is None else workspace
        super().__init__(workspace, trace)

    def clear_changes(self):
        self.var_handler.clear_changes()

    def marcel_usage(self):
        return 'api'


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

        def __init__(self, module_name, symbol, name):
            assert module_name is not None
            assert name is not None
            self.module_name = module_name
            self.symbol = symbol
            self.name = name
            self.id = f'{module_name}/{"" if symbol is None else symbol}/{name}'

        def __repr__(self):
            buffer = [f'import({self.module_name}']
            if self.symbol is not None:
                buffer.append(f' {self.symbol}')
            if self.name is not None:
                buffer.append(f' as {self.name}')
            buffer.append(')')
            return ''.join(buffer)

        def __hash__(self):
            return hash(self.id)

        def __eq__(self, other):
            return self.id == other.id

    def __init__(self, workspace, trace=None):
        super().__init__(workspace, trace)
        # Vars defined during startup
        self.startup_vars = None
        # Support for pos()
        self.current_op = None
        # Symbols imported need special handling
        self.var_handler.add_immutable_vars('pos')

    # Don't pickle everything

    def initial_namespace(self):
        initial_namespace = super().initial_namespace()
        initial_namespace.update({
            'WORKSPACE': self.workspace.name,
            'PROMPT': [EnvironmentInteractive.DEFAULT_PROMPT],
            'BOLD': marcel.object.color.Color.BOLD,
            'ITALIC': marcel.object.color.Color.ITALIC,
            'COLOR_SCHEME': marcel.object.color.ColorScheme(),
            'Color': marcel.object.color.Color,
            'pos': lambda: self.current_op.pos(),
            'o': marcel.structish.o})
        for key, value in marcel.builtin.__dict__.items():
            if not key.startswith('_'):
                initial_namespace[key] = value
        return initial_namespace

    def pid(self):
        return self.locations.pid

    def never_mutable(self):
        vars = set(super().never_mutable())
        vars.update({'MARCEL_VERSION', 'HOME', 'USER', 'HOST', 'WORKSPACE'})
        return vars

    def read_config(self):
        config_path = self.locations.config_ws_startup(self.workspace)
        if config_path.exists():
            with open(config_path) as config_file:
                config_source = config_file.read()
            # Execute the config file. Imported and newly-defined symbols go into locals, which
            # will then be added to self.namespace, for use in the execution of op functions.
            locals = dict()
            try:
                exec(config_source, self.workspace.namespace, locals)
            except Exception as e:
                raise marcel.exception.StartupScriptException(self.workspace, e)
            self.workspace.namespace.update(locals)

    def check_nesting(self):
        return EnvironmentScript.CheckNesting(self)

    def set_function_globals(self, function):
        function.set_globals(self.vars())

    def marcel_usage(self):
        return 'script'

    def mark_possibly_changed(self, var):
        self.var_handler.add_changed_var(var)

    def import_module(self, module_name, symbol, name):
        try:
            module = importlib.import_module(module_name)
            if symbol is None:
                if name is None:
                    name = module_name
                self.var_handler.setvar(name, module, save=False)
            elif symbol == '*':
                for name, value in module.__dict__.items():
                    if not name.startswith('_'):
                        self.var_handler.setvar(name, value, save=False)
            else:
                value = module.__dict__[symbol]
                if name is None:
                    name = symbol
                self.var_handler.setvar(name, value, save=False)
            self.imports.add(EnvironmentScript.Import(module_name, symbol, name))
        except ModuleNotFoundError:
            raise marcel.exception.ImportException(f'Module {module_name} not found.')
        except KeyError:
            raise marcel.exception.ImportException(f'{symbol} is not defined in {module_name}')

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
    def is_immutable(x):
        return callable(x) or marcel.util.one_of(x, (int,
                                                     float,
                                                     str,
                                                     bool,
                                                     tuple,
                                                     marcel.core.PipelineExecutable))


class EnvironmentInteractive(EnvironmentScript):

    DEFAULT_PROMPT = f'M {marcel.version.VERSION} $ '

    def __init__(self, workspace, trace=None):
        super().__init__(workspace, trace)
        # Actual config path. Needed to reread config file in case of modification.
        self.config_path = None
        self.reader = None
        self.next_command = None
        self.var_handler.add_immutable_vars('PROMPT',
                                            'BOLD',
                                            'ITALIC',
                                            'COLOR_SCHEME',
                                            'Color')

    def prompt(self):
        def prompt_dir():
            dir = self.getvar('PWD')
            home = self.getvar('HOME')
            if self.workspace.is_default():
                return '~' + dir[len(home):] if dir.startswith(home) else dir
            else:
                try:
                    workspace_home = self.workspace.home()
                    if workspace_home:
                        dir = pathlib.Path(dir).expanduser()
                        workspace_home = pathlib.Path(workspace_home).expanduser()
                        prompt_dir = dir.relative_to(workspace_home).as_posix()
                        if prompt_dir == '.':
                            prompt_dir = ''
                    else:
                        prompt_dir = dir
                    return prompt_dir
                except ValueError:
                    # dir is not under home
                    return dir

        # Set PROMPT_DIR in case PROMPT uses it.
        self.setvar('PROMPT_DIR', prompt_dir())
        return self.prompt_string(self.getvar('PROMPT'))

    def prompt_string(self, prompt_pieces):
        try:
            buffer = []
            color = None
            for x in prompt_pieces:
                # In each iteration, we have a color, a prompt component, or a function creating a prompt component.
                # In the last two cases, append the prompt component to the buffer, colorizing if color is defined.
                if isinstance(x, marcel.object.color.Color):
                    color = x
                    x = None
                elif isinstance(x, str):
                    pass
                elif callable(x):
                    # Set up the namespace for calling the function. Updating __globals__ with a NestedNamespace
                    # seems to break things so that the invocation (x()) raises an AssertionError. Need a genuine
                    # dict for the update.
                    x.__globals__.update(dict(self.workspace.namespace))
                    x = x()
                else:
                    raise marcel.exception.KillShellException(f'Invalid prompt component: {x}')
                if x:
                    x = str(x)
                    buffer.append(marcel.util.colorize(x, color) if color else x)
            return ''.join(buffer)
        except Exception as e:
            print(f'Bad prompt definition in {prompt_pieces}: ({type(e)}) {e}', file=sys.stderr)
            return EnvironmentInteractive.DEFAULT_PROMPT

    def take_next_command(self):
        command = self.next_command
        self.next_command = None
        return command


class Trace(object):

    def __init__(self):
        self.tracefile = None
        self.description = None

    def is_enabled(self):
        return self.tracefile is not None

    def enable(self, target):
        if target is sys.stdout:
            self.tracefile = sys.stdout
            self.description = 'stdout'
        else:
            try:
                self.tracefile = open(target, 'a')
                self.description = target
            except Exception as e:
                raise marcel.exception.KillCommandException(
                    f'Unable to start tracing to {target}: {e}')

    def disable(self):
        if self.tracefile and self.tracefile is not sys.stdout:
            self.tracefile.close()
        self.tracefile = None
        self.description = None

    # output argument: output from the execution of the op
    def write(self, phase, op, output=None):
        assert self.tracefile
        if output is None:
            print(f'{op} {phase}', file=self.tracefile, flush=True)
        else:
            print(f'{op} {phase} -> {output}', file=self.tracefile, flush=True)

    def print_status(self):
        if self.tracefile is None:
            print('tracing is off')
        elif self.tracefile is sys.stdout:
            print(f'tracing to {self.description}')
