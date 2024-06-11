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

import atexit
import multiprocessing
import os
import pathlib
import readline
import sys
import time

import marcel.builtin
import marcel.core
import marcel.env
import marcel.exception
import marcel.job
import marcel.locations
import marcel.persistence.migration
import marcel.persistence.persistence
import marcel.multilinereader
import marcel.object.workspace
import marcel.opmodule
import marcel.parser
import marcel.reservoir
import marcel.tabcompleter
import marcel.util
import marcel.version

Workspace = marcel.object.workspace.Workspace
HISTORY_LENGTH = 1000

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


class Reader(marcel.multilinereader.MultiLineReader):

    def __init__(self, env, history_file):
        super().__init__(history_file=history_file)
        self.env = env

    def take_edited_command(self):
        edited_command = self.env.edited_command
        self.env.edited_command = None
        return edited_command


class Main(object):

    def __init__(self, env, testing=None):
        self.main_pid = os.getpid()
        self.env = env

    # Main

    def shutdown(self, restart=False):
        assert False


class MainAPI(Main):

    def __init__(self, env):
        super().__init__(env)
        self.env.enforce_var_immutability()
        atexit.register(self.shutdown)

    # Main

    def shutdown(self, restart=False):
        namespace = self.env.namespace
        return namespace


class MainScript(Main):

    # If a test is being run, testing is set to a directory pretending to be the user's home.
    def __init__(self, env, workspace, testing=None, initial_config=DEFAULT_CONFIG):
        super().__init__(env, testing)
        self.workspace = workspace
        # Ensure that on-disk state is set up and correct.
        if env.locations.fresh_install():
            initialize_persistent_config_and_data(env, initial_config)
        marcel.persistence.persistence.validate_all(env, self.handle_persistence_validation_errors)
        if not Workspace.default().exists(env):
            # The default workspace was found to be broken, and was removed. Create a new one.
            Workspace.default().create_on_disk(env, DEFAULT_CONFIG)
        # Restore workspace state
        if self.workspace.exists(env):
            env.restore_persistent_state_from_workspace()
        else:
            self.workspace.does_not_exist()
        self.testing = testing
        self.config_time = time.time()
        startup_vars = self.read_config()
        self.env.enforce_var_immutability(startup_vars)
        self.needs_restart = False
        if not testing and not self.env.locations.fresh_install():
            marcel.persistence.migration.migrate()
        atexit.register(self.shutdown)

    def read_config(self):
        # Comparing keys_before/after tells us what vars were defined by the startup script.
        keys_before = set(self.env.namespace.keys())
        # Make sure that never mutable vars aren't modified during startup.
        never_mutable_vars = self.env.never_mutable()
        never_mutable_before = {var: value for (var, value) in self.env.vars().items()
                                if var in never_mutable_vars}
        # Read the startup script, and then any marcel code contained in it.
        self.env.read_config()
        self.run_startup_scripts()
        # Find the vars defined during startup
        keys_after = set(self.env.namespace.keys())
        startup_vars = keys_after - keys_before
        # Check that never mutable vars didn't change.
        never_mutable_after = {var: value for (var, value) in self.env.vars().items()
                               if var in never_mutable_vars}
        for var in never_mutable_before.keys():
            before_value = never_mutable_before.get(var, None)
            after_value = never_mutable_after.get(var, None)
            if before_value != after_value:
                raise marcel.exception.KillShellException(f'Startup script must not modify the value of {var}.')
        return startup_vars

    # Main

    def parse_and_run_command(self, text):
        if text:
            try:
                parser = marcel.parser.Parser(text, self.env)
                pipeline = parser.parse()
                if not pipeline.last_op().op_name() == 'write':
                    pipeline.append(marcel.opmodule.create_op(self.env, 'write'))
                command = marcel.core.Command(text, pipeline)
                self.execute_command(command, pipeline)
            except marcel.parser.EmptyCommand:
                pass
            except marcel.exception.KillCommandException as e:
                marcel.util.print_to_stderr(self.env, e)
            except marcel.exception.KillAndResumeException:
                # Error handler printed the error
                pass

    def shutdown(self, restart=False):
        try:
            self.workspace.close(self.env, restart)
        except:
            pass
        # If we're shutting down for real (not restarting) then the default workspace needs to be closed too.
        if not restart:
            try:
                Workspace.default().close(self.env, restart)
            except:
                pass
        # The current main is about to be obsolete, but it still exists, and is registered with atexit,
        # keeping it alive, I think. So it's shutdown handler gets run on shutdown. atexit.unregister
        # prevents this, and only the current Main's shutdown will run, on shutdown.
        atexit.unregister(self.shutdown)

    # MainScript

    def execute_command(self, command, pipeline):
        command.execute(self.env)

    def run_startup_scripts(self):
        startup_scripts = self.env.getvar('STARTUP_SCRIPTS')
        for script in startup_scripts:
            if type(script) is str:
                for command in commands_in_script(script):
                    self.parse_and_run_command(command)

    # Internal

    def handle_persistence_validation_errors(self, errors):
        if len(errors) > 0:
            now = time.time()
            broken_ws_config = self.env.locations.config_bws() / str(now)
            broken_ws_data = self.env.locations.data_bws() / str(now)
            marcel.util.print_to_stderr(self.env,
                                        f'Damaged workspaces have been detected. Their contents will be moved to:'
                                        f'\n    {broken_ws_config}'
                                        f'\n    {broken_ws_data}')
            started_in_broken_ws = False
            for validation_error in errors:
                marcel.util.print_to_stderr(self.env, str(validation_error))
                ws_name = validation_error.workspace_name
                broken_ws = Workspace (ws_name)
                started_in_broken_ws = started_in_broken_ws or (self.env.workspace.name == ws_name)
                broken_ws.mark_broken(self.env, now)
            if started_in_broken_ws:
                # This marks this MainScript object as needing a restart. Don't want to continue with a broken
                # workspace, but throwing a ReconfigureException right now (during MainScript.__init__)
                # is messy, since we're then shutting down an incompletely initialized main.
                self.needs_restart = True
                message = ('Default workspace was damaged. Starting in a recreated default workspace.'
                           if self.workspace.is_default() else
                           f'Selected workspace {self.workspace.name} is damaged, starting in default workspace.')
                marcel.util.print_to_stderr(self.env, message)


class MainInteractive(MainScript):

    def __init__(self, old_main, env, workspace, testing=None, initial_config=DEFAULT_CONFIG):
        super().__init__(env, workspace, testing, initial_config)
        self.tab_completer = marcel.tabcompleter.TabCompleter(self)
        try:
            self.reader = self.initialize_reader()
        except FileNotFoundError:
            # Probably a damaged workspace. Restart in default workspace.
            self.needs_restart = True
        self.job_control = marcel.job.JobControl.start(self.env, self.update_namespace)
        self.input = None
        if old_main:
            # input records the current line of input. If a ReconfigureException is thrown, the old Main's input field
            # carries the input to the new Main, allowing the command to execute.
            self.input = old_main.input

    # Main

    def shutdown(self, restart=False):
        try:
            self.reader.close()
        except:
            pass
        try:
            self.job_control.shutdown()
        except:
            pass
        return super().shutdown(restart)

    # MainScript

    def execute_command(self, command, pipeline):
        if self.testing or pipeline.first_op().run_in_main_process():
            command.execute(self.env)
        else:
            self.job_control.create_job(command)

    # MainInteractive

    def run(self):
        interactive = sys.stdin.isatty()
        try:
            while True:
                try:
                    if self.input is None:
                        prompts = self.env.prompts() if interactive else (None, None)
                        self.input = self.reader.input(*prompts)
                    # else: Restarted main, and self.input was from the previous incarnation.
                    self.check_for_config_update()
                    self.parse_and_run_command(self.input)
                    self.input = None
                    self.job_control.wait_for_idle_foreground()
                except KeyboardInterrupt:  # ctrl-C
                    print()
        except EOFError:
            if interactive:
                print()
            # else: not a tty, and we don't want an extra line at end of script execution.

    # Internal

    def initialize_reader(self):
        readline.set_history_length(HISTORY_LENGTH)
        readline.parse_and_bind('tab: complete')
        readline.parse_and_bind('set editing-mode emacs')
        readline.parse_and_bind('set completion-query-items 50')
        readline.set_pre_input_hook(self.insert_edited_command)
        self.env.reader = Reader(self.env, self.env.locations.data_ws_hist(self.workspace))
        return self.env.reader

    def insert_edited_command(self):
        command = self.reader.take_edited_command()
        if command:
            readline.insert_text(command)
            readline.redisplay()

    def update_namespace(self, child_namespace_changes):
        # pwd requires special handling
        try:
            pwd = child_namespace_changes['PWD']
            self.env.dir_state().change_current_dir(pathlib.Path(pwd))
        except KeyError:
            # PWD wasn't changed
            pass
        for var, value in child_namespace_changes.items():
            self.env.setvar(var, value)

    def check_for_config_update(self):
        config_path = self.env.locations.config_ws_startup(self.workspace)
        config_mtime = config_path.stat().st_mtime if config_path.exists() else 0
        if self.config_time and config_mtime > self.config_time:
            # The workspace argument is used to open a new workspace, different from the previous one, e.g.
            # on ws -c, or ws -o. We aren't changing the workspace here, so pass None.
            raise marcel.exception.ReconfigureException(workspace=None)


def commands_in_script(script):
    command = ''
    for line in script.split('\n'):
        if len(line.strip()) > 0:
            if line.endswith('\\'):
                command += line[:-1]
            else:
                command += line
                yield command
                command = ''
    if len(command) > 0:
        yield command


def fail(message):
    print(message, file=sys.stderr)
    exit(1)


def usage(exit_code=1):
    usage = '''
    marcel [WORKSPACE] [-e|--execute SCRIPT] [--mpstart fork|spawn|forkserver]
    marcel [-h|--help]
    
    Run marcel, interactively unless a SCRIPT is provided.
    
    if WORKSPACE is specified, then marcel will open the named WORKSPACE before 
    executing commands interactively or commands from the SCRIPT.
    
    This usage message is obtained by running marcel with the -h or --help
    flag. For more detailed help, run marcel interactively and use the "help" command.
    
    Leave out --mpstart unless you really know what you're doing, or you're desperate. 
    It defaults to fork.
'''
    print(usage, file=sys.stderr)
    sys.exit(exit_code)


# --mpstart: fork/spawn/forkserver. Use fork if not specified
def args():
    workspace= None
    flags = ('-e', '--execute', '-h', '--help', '--mpstart',)
    mpstart = 'fork'
    script = None
    flag = None
    first_arg = True
    for arg in sys.argv[1:]:
        if first_arg and not arg.startswith('-'):
            workspace = arg
        elif arg in flags:
            flag = arg
            if flag in ('-h', '--help'):
                usage(0)
        elif arg.startswith('-'):
            usage()
        else:
            # arg is a flag value
            assert flag is not None
            if flag in ('-e', '--execute'):
                script = arg
            elif flag == '--mpstart':
                if arg in ('fork', 'spawn', 'forkserver'):
                    mpstart = arg
                else:
                    usage()
            flag = None
        first_arg = False
    return workspace, script, mpstart


def main_interactive_run(locations, workspace):
    def restart_in_default_workspace():
        raise marcel.exception.ReconfigureException(Workspace.default())

    main = None
    trace = None
    while True:
        try:
            env = marcel.env.EnvironmentInteractive.create(locations, workspace, trace)
        except Exception as e:
            # Something ws-related? Try starting in default
            workspace = Workspace.default()
            env = marcel.env.EnvironmentInteractive.create(locations, workspace, trace)
            marcel.util.print_to_stderr(
                env,
                f'Caught {type(e)} during startup. Starting in default workspace. {str(e)}')
        main = MainInteractive(main, env, workspace)
        try:
            if main.needs_restart:
                restart_in_default_workspace()
            main.run()
            break
        except marcel.exception.ReconfigureException as e:
            trace = main.env.trace
            main.shutdown(restart=True)
            if e.workspace_to_open is None:
                # Reconfiguration is due to modified startup script. Same workspace, keep main.input so it is rerun.
                workspace = main.workspace
            else:
                # Reconfiguration is due to change of workspace. main.input was the workspace command
                # that caused the reconfiguration, so don't rerun it.
                workspace = e.workspace_to_open
                main.input = None


def main_script_run(locations, workspace, script_path):
    try:
        with open(script_path, 'r') as script_file:
            script = script_file.read()
    except FileNotFoundError:
        fail(f'File not found: {script_path}')
    commands = commands_in_script(script)
    env = marcel.env.EnvironmentScript.create(locations, workspace)
    main = MainScript(env, workspace)
    for command in commands:
        try:
            main.parse_and_run_command(command)
        except marcel.exception.ReconfigureException as e:
            main.shutdown(restart=True)
            # e.workspace_to_open implies startup script change, which shouldn't happen
            # while running a script.
            assert e.workspace_to_open is not None
            workspace = e.workspace_to_open
            env = marcel.env.EnvironmentScript.create(locations, workspace, main.env.trace)
            main = MainScript(env, workspace)


def initialize_persistent_config_and_data(env, initial_config):
    locations = env.locations
    # These calls ensure the config and data directories exist.
    locations.config()
    locations.config_ws()
    locations.config_bws()
    locations.data()
    locations.data_ws()
    locations.data_bws()
    # Version
    locations.config_version().write_text(marcel.version.VERSION)
    locations.config_version().chmod(0o400)
    # Default workspace
    Workspace.default().create_on_disk(env, initial_config)


def main():
    workspace_name, script, mpstart = args()
    multiprocessing.set_start_method(mpstart)
    workspace = Workspace.named(workspace_name)
    locations = marcel.locations.Locations()
    if script is None:
        main_interactive_run(locations, workspace)
    else:
        main_script_run(locations, workspace, script)


if __name__ == '__main__':
    try:
        main()
    except (marcel.exception.KillShellException,
            marcel.exception.KillCommandException) as e:
        # KillCommandException is normally handled deeper down. But starting marcel
        # on the command line, and specifying a workspace, e.g. "marcel foobar" will
        # raise KCE if foobar is already in use by another process. It would be incorrect to
        # raise KSE instead for switching to a workspace from a marcel commandd.
        print(str(e), file=sys.stderr)
    except marcel.exception.ExitException:
        sys.exit(0)
