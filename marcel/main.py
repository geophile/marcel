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
import sys
import time

import marcel.builtin
import marcel.core
import marcel.env
import marcel.exception
import marcel.job
import marcel.locations
import marcel.persistence.persistence
import marcel.persistence.storagelayout
import marcel.object.workspace
import marcel.opmodule
import marcel.parser
import marcel.pipeline
import marcel.reader
import marcel.reservoir
import marcel.tabcompleter
import marcel.util
import marcel.version

Workspace = marcel.object.workspace.Workspace


class Main(object):

    def __init__(self, env, testing=None):
        self.main_pid = os.getpid()
        self.env = env
        self.job_control = None
        atexit.register(self.shutdown)

    # Main

    def shutdown(self, restart=False):
        if self.job_control:
            try:
                self.job_control.shutdown()
            except:
                pass
        try:
            self.env.workspace.close(self.env, restart)
        except:
            pass
        # If we're shutting down for real (not restarting) then the default workspace needs to be closed too.
        if not restart:
            try:
                Workspace.default().close(self.env, restart)
            except:
                pass
        # The current main is about to be obsolete, but it still exists, and is registered with atexit,
        # keeping it alive, I think. So its shutdown handler gets run on shutdown. atexit.unregister
        # prevents this, and only the current Main's shutdown will run, on shutdown.
        atexit.unregister(self.shutdown)


class MainAPI(Main):

    def __init__(self, env):
        super().__init__(env)


class MainScript(Main):

    # If a test is being run, testing is set to a directory pretending to be the user's home.
    def __init__(self, env, testing=None):
        super().__init__(env, testing)
        self.testing = testing
        self.config_time = time.time()
        self.needs_restart = False
        marcel.persistence.persistence.validate_all(self.handle_persistence_validation_errors)

    # Main

    def parse_and_run_command(self, text):
        if text:
            env = self.env
            try:
                env.workspace.namespace.set_env(env)
                parser = marcel.parser.Parser(text, env)
                pipeline = parser.parse()
                assert type(pipeline) is marcel.pipeline.PipelineMarcel, f'({type(pipeline)}) {pipeline}'
                pipeline.ensure_terminal_write(env)
                command = marcel.core.Command(text, pipeline)
                self.execute_command(command, pipeline)
            except marcel.parser.EmptyCommand:
                pass
            except marcel.exception.KillCommandException as e:
                marcel.util.print_to_stderr(env, e)
            except marcel.exception.KillAndResumeException:
                # Error handler printed the error
                pass

    # MainScript

    def execute_command(self, command, pipeline):
        command.execute(self.env)

    # Internal

    def handle_persistence_validation_errors(self, broken_workspace_names, errors):
        if len(errors) > 0:
            now = time.time()
            broken_ws_config = self.env.locations.config_bws() / str(now)
            broken_ws_data = self.env.locations.data_bws() / str(now)
            marcel.util.print_to_stderr(self.env,
                                        f'Damaged workspaces have been detected: {sorted(broken_workspace_names)}. '
                                        f'Their contents will be moved to:'
                                        f'\n    {broken_ws_config}'
                                        f'\n    {broken_ws_data}')
            started_in_broken_ws = False
            for validation_error in errors:
                marcel.util.print_to_stderr(self.env, str(validation_error))
                ws_name = validation_error.workspace_name
                broken_ws = Workspace (ws_name)
                started_in_broken_ws = started_in_broken_ws or (self.env.workspace.name == ws_name)
                broken_ws.mark_broken(now)
            if started_in_broken_ws:
                # This marks this MainScript object as needing a restart. Don't want to continue with a broken
                # workspace, but throwing a ReconfigureException right now (during MainScript.__init__)
                # is messy, since we're then shutting down an incompletely initialized main.
                self.needs_restart = True
                message = ('Default workspace was damaged. Starting in a recreated default workspace.'
                           if self.env.workspace.is_default() else
                           f'Selected workspace {self.env.workspace.name} is damaged, starting in default workspace.')
                marcel.util.print_to_stderr(self.env, message)

    def run_startup_scripts(self):
        startup_scripts = self.env.getvar('STARTUP_SCRIPTS')
        for script in startup_scripts:
            if type(script) is not str:
                raise marcel.exception.KillCommandException(
                    'Startup scripts, specified by run_on_startup(), must be strings')
            for command in commands_in_script(script):
                self.parse_and_run_command(command)

    @staticmethod
    def update_version_file():
        def installed_version():
            version_file_path = locations.config_version()
            if version_file_path.exists():
                with open(version_file_path) as version_file:
                    installed_version = version_file.readline().strip()
            else:
                installed_version = '0.0.0'
            return installed_version

        locations = marcel.locations.Locations()
        if installed_version() < marcel.version.VERSION:
            version_file_path = locations.config_version()
            version_file_path.touch(exist_ok=True)
            version_file_path.chmod(0o600)
            version_file_path.write_text(f'{marcel.version.VERSION}\n')
            version_file_path.chmod(0o400)


class MainInteractive(MainScript):

    def __init__(self, old_main, env, testing=None):
        super().__init__(env, testing)
        self.tab_completer = marcel.tabcompleter.TabCompleter(env)
        try:
            self.reader = marcel.reader.Reader(self.env)
            self.env.reader = self.reader  # So that ops, specifically edit, has access to the reader.
        except FileNotFoundError:
            # Probably a damaged workspace. Restart in default workspace.
            self.needs_restart = True
        self.job_control = marcel.job.JobControl.start(self.env, self.update_namespace)
        self.input = None
        if old_main:
            # input records the current line of input. If a ReconfigureException is thrown, the old Main's input field
            # carries the input to the new Main, allowing the command to execute.
            self.input = old_main.input

    # MainScript

    def execute_command(self, command, pipeline):
        if self.testing or pipeline.run_in_main_process():
            command.execute(self.env)
        else:
            self.job_control.create_job(command)

    # MainInteractive

    def run(self):
        self.env.go_to_current_dir()
        interactive = sys.stdin.isatty()
        try:
            while True:
                try:
                    self.input = self.env.take_next_command()
                    if self.input is None:
                        self.input = (self.reader.input() if interactive
                                      else input())
                    # else: Restarted main, and self.input was from the previous incarnation.
                    self.check_for_config_update()
                    self.parse_and_run_command(self.input)
                    self.input = None
                    self.job_control.wait_for_idle_foreground()
                except KeyboardInterrupt:  # ctrl-C
                    print()
        except EOFError:  # ctrl-d
            if interactive:
                print()
            # else: not a tty, and we don't want an extra line at end of script execution.

    # Internal

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
        config_path = self.env.locations.config_ws_startup(self.env.workspace)
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


def main_interactive_run():
    def restart_in_default_workspace():
        raise marcel.exception.ReconfigureException(Workspace.default())

    def env_and_main(old_env, old_main, workspace):
        try:
            env = marcel.env.EnvironmentInteractive.create(workspace=workspace, trace=trace)
        except Exception as e:
            # Something ws-related? Try starting in default
            marcel.util.print_to_stderr(
                old_env,
                f'Caught {type(e)} during startup. Starting in default workspace. {str(e)}')
            return env_and_main(old_env, old_main, Workspace.default())
        assert env is not None
        try:
            main = MainInteractive(old_main, env)
            main.run_startup_scripts()
            return env, main
        except marcel.exception.StartupScriptException as e:
            if workspace.is_default():
                marcel.util.print_to_stderr(env, 'Error in startup script for default workspace.')
                marcel.util.print_to_stderr(env, 'Fix the startup script and try again.')
                sys.exit(1)
            else:
                print(str(e), file=sys.stderr)
                marcel.util.print_to_stderr(env, 'Trying default workspace ...')
                return env_and_main(old_env, old_main, Workspace.default())

    main = None
    trace = None
    workspace = Workspace.default()
    while True:
        env, main = env_and_main(None, main, workspace)
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
                workspace = env.workspace
            else:
                # Reconfiguration is due to change of workspace. main.input was the workspace command
                # that caused the reconfiguration, so don't rerun it.
                workspace = e.workspace_to_open
                main.input = None


def main_script_run(script):
    commands = commands_in_script(script)
    workspace = Workspace.default()
    env = marcel.env.Environment.create(workspace=workspace)
    main = MainScript(env)
    main.run_startup_scripts()
    for command in commands:
        try:
            main.parse_and_run_command(command)
        except marcel.exception.ReconfigureException as e:
            main.shutdown(restart=True)
            # e.workspace_to_open implies startup script change, which shouldn't happen
            # while running a script.
            assert e.workspace_to_open is not None
            workspace = e.workspace_to_open
            env = marcel.env.Environment.create(workspace=workspace, trace=main.env.trace)
            main = MainScript(env)


def read_heredoc():
    lines = []
    while len(line := sys.stdin.readline().strip()) != 0:
        lines.append(line)
    return '\n'.join(lines)

def read_script(script_path):
    try:
        with open(script_path, 'r') as script_file:
            script = script_file.read()
    except FileNotFoundError:
        fail(f'File not found: {script_path}')
    return script


def main():
    multiprocessing.set_start_method(os.getenv('MARCEL_MULTIPROCESSING_START_METHOD', default='spawn'))
    marcel.persistence.storagelayout.ensure_current(testing=False)
    # Check that default workspace exists
    if not Workspace.default().exists():
        Workspace.default().does_not_exist()
    input_source = marcel.util.InputSource()
    started = False
    while not started:
        try:
            if input_source.interactive():
                main_interactive_run()
            elif input_source.script():
                main_script_run(read_script(sys.argv[1]))
            elif input_source.heredoc():
                main_script_run(read_heredoc())
            else:
                raise marcel.exception.KillShellException('Unable to determine input source!')
            started = True
        except marcel.exception.StartupScriptException as e:
            print(str(e), file=sys.stderr)
        except:
            raise


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
