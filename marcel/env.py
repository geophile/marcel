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
import os
import pathlib
import socket
import sys

import marcel.builtin
import marcel.builtins
import marcel.cliargs
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


class CheckNesting(object):

    def __init__(self, env):
        self.env = env
        self.depth = None

    def __enter__(self):
        self.depth = self.env.vars().n_scopes()

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self.env.vars().n_scopes() == self.depth, self.env.vars().n_scopes()
        self.depth = None


class CheckNestingNoop(object):

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Environment(object):

    def __init__(self, usage, workspace=None, trace=None):
        if workspace is None:
            from marcel.object.workspace import Workspace
            workspace = Workspace.default()
        self.usage = usage
        self.workspace = workspace
        self.locations = marcel.locations.Locations()
        self.directory_state = marcel.directorystate.DirectoryState(self)
        self.config_path = None
        self.op_modules = marcel.opmodule.import_op_modules()
        self.current_op = None  # Needed for pos()
        self.trace = trace if trace else Trace()
        self.var_handler.add_immutable_vars(('BOLD',
                                             'COLOR_SCHEME',
                                             'Color',
                                             'DIRS',
                                             'HOME',
                                             'HOST'
                                             'ITALIC',
                                             'MARCEL_VERSION',
                                             'pos',
                                             'PROMPT',
                                             'PWD',
                                             'USER'))

    # TODO: These properties are scaffolding during move of namespace to Workspace
    @property
    def namespace(self):
        return self.workspace.namespace

    @property
    def var_handler(self):
        return self.workspace.var_handler

    def initial_namespace(self):
        def home_dir():
            try:
                return pathlib.Path.home().resolve().as_posix()
            except FileNotFoundError:
                raise marcel.exception.KillShellException(
                    'Home directory does not exist!')
        def current_dir():
            try:
                return pathlib.Path.cwd().resolve().as_posix()
            except FileNotFoundError:
                return home_dir()
        builtins = marcel.builtins.Builtins()
        builtins['MARCEL_VERSION'] = lambda env: marcel.version.VERSION
        builtins['HOME'] = lambda env: home_dir()
        builtins['PWD'] = lambda env: current_dir()
        builtins['DIRS'] = lambda env: [current_dir()]
        builtins['USER'] = lambda env: getpass.getuser()
        builtins['HOST'] = lambda env: socket.gethostname()
        builtins['parse_args'] = lambda env: lambda usage=None, **kwargs: marcel.cliargs.parse_args(env, usage, **kwargs)
        builtins['WORKSPACE'] = lambda env: self.workspace.name
        builtins['pos'] = lambda env: lambda: self.current_op.pos()
        builtins['o'] = lambda env: marcel.structish.o
        builtins['PROMPT'] = lambda env: [EnvironmentInteractive.DEFAULT_PROMPT]
        builtins['BOLD'] = lambda env: marcel.object.color.Color.BOLD
        builtins['ITALIC'] = lambda env: marcel.object.color.Color.ITALIC
        builtins['COLOR_SCHEME'] = lambda env: marcel.object.color.ColorScheme()
        builtins['Color'] = lambda env: marcel.object.color.Color
        builtins['set_db_default'] = lambda env: lambda db: env.workspace.var_handler.setvar('DB_DEFAULT', db)
        for key, value in marcel.builtin.__dict__.items():
            if not key.startswith('_'):
                builtins[key] = lambda env: value
        return builtins

    def dir_state(self):
        return self.directory_state

    def enforce_var_immutability(self):
        self.var_handler.enforce_immutability()

    def hasvar(self, var):
        return self.var_handler.hasvar(var)

    def getvar(self, var):
        return self.var_handler.getvar(var)

    def setvar(self, var, value):
        self.var_handler.setvar(var, value)

    def setvar_with_source(self, var, value, source):
        self.var_handler.setvar(var, value, source=source)

    def delvar(self, var):
        return self.var_handler.delvar(var)

    def vars(self):
        return self.var_handler.vars()

    def cluster(self, name):
        cluster = None
        if isinstance(name, str):
            x = self.getvar(name)
            if type(x) is marcel.object.cluster.Cluster:
                cluster = x
        return cluster

    def check_nesting(self):
        return CheckNestingNoop() if self.api_usage() else CheckNesting(self)

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
        return self.usage

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
               trace=None,
               usage='script'):
        assert usage in ('script', 'api'), usage
        # Don't use a default value for workspace. Default value expressions are evaluted
        # on import, which may be too early. Discovered this gotcha on a unit test. Unit tests
        # set HOME (in os.environ). But Workspace.default() creates a Locations object which
        # depends on HOME. So Locations were wrong because HOME had not yet been reset for the test.
        if workspace is None:
            import marcel.object.workspace
            workspace = marcel.object.workspace.Workspace.default()
        env = cls(workspace=workspace, trace=trace, usage=usage)
        initial_namespace = env.initial_namespace()
        workspace.open(env, initial_namespace)
        assert (usage == 'api') == (globals is not None)
        if globals is not None:
            workspace.namespace.update(globals)
        return env

    # Vars that are not mutable even during startup. I.e., startup script can't modify them.
    @staticmethod
    def never_mutable():
        return {'MARCEL_VERSION', 'HOME', 'USER', 'HOST', 'WORKSPACE'}



class EnvironmentScript(Environment):

    def mark_possibly_changed(self, var):
        self.var_handler.add_changed_var(var)

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


class EnvironmentInteractive(EnvironmentScript):

    DEFAULT_PROMPT = f'M {marcel.version.VERSION} $ '

    def __init__(self, usage, workspace, trace=None):
        super().__init__(usage, workspace, trace)
        self.reader = None
        self.next_command = None

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
                    # x.__globals__.update(dict(self.workspace.namespace))
                    x = x()
                else:
                    raise marcel.exception.KillShellException(f'Invalid prompt component: {x}')
                if x:
                    x = str(x)
                    buffer.append(marcel.util.colorize(x, color) if color else x)
            return ''.join(buffer)
        except Exception as e:
            print(f'Bad prompt definition in {prompt_pieces}: ({type(e)}) {e}', file=sys.stderr)
            marcel.util.print_stack_of_current_exception()
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
