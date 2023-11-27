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
import marcel.multilinereader
import marcel.opmodule
import marcel.parser
import marcel.reservoir
import marcel.tabcompleter
import marcel.util

HISTORY_LENGTH = 1000


class Reader(marcel.multilinereader.MultiLineReader):

    def __init__(self, env, history_file):
        super().__init__(history_file=history_file)
        self.env = env

    def take_edited_command(self):
        edited_command = self.env.edited_command
        self.env.edited_command = None
        return edited_command


class ReloadConfigException(BaseException):

    def __init__(self):
        super().__init__()


class Main(object):

    def __init__(self):
        self.main_pid = os.getpid()
        self.env = None
        atexit.register(self.shutdown)

    # Main

    def shutdown(self, restart=False):
        assert False


# MainScript is the parent of MainInteractive, and provides much of its logic.
class MainScript(Main):

    def __init__(self, config_file, testing=False):
        super().__init__()
        try:
            self.env = marcel.env.EnvironmentScript.create()
        except marcel.exception.KillCommandException as e:
            print(f'Cannot start marcel: {e}', file=sys.stderr)
            sys.exit(1)
        except marcel.exception.KillShellException as e:
            print(f'Cannot start marcel: {e}', file=sys.stderr)
            sys.exit(1)
        self.testing = testing
        self.config_time = time.time()
        self.env.read_config(config_file)
        self.run_startup()

    # Main

    def parse_and_run_command(self, text):
        if text:
            try:
                parser = marcel.parser.Parser(text, self)
                pipeline = parser.parse()
                pipeline.set_error_handler(MainScript.default_error_handler)
                if not pipeline.last_op().op_name() == 'write':
                    pipeline.append(marcel.opmodule.create_op(self.env, 'write'))
                command = marcel.core.Command(text, pipeline)
                self.execute_command(command, pipeline)
            except marcel.parser.EmptyCommand:
                pass
            except marcel.exception.KillCommandException as e:
                marcel.util.print_to_stderr(e, self.env)
            except marcel.exception.KillAndResumeException:
                # Error handler printed the error
                pass

    def shutdown(self, restart=False):
        if not restart:
            marcel.reservoir.shutdown(self.main_pid)

    # MainScript

    def execute_command(self, command, pipeline):
        command.execute(self.env)

    def run_startup(self):
        # Inside the startup script, variables that are otherwise immutabe, aren't.
        with self.env.no_mutability_check():
            run_on_startup = self.env.getvar('RUN_ON_STARTUP')
            if run_on_startup:
                if type(run_on_startup) is str:
                    self.run_script(run_on_startup)
                else:
                    fail(f'RUN_ON_STARTUP must be a string')

    def run_script(self, script):
        command = ''
        for line in script.split('\n'):
            if len(line.strip()) > 0:
                if line.endswith('\\'):
                    command += line[:-1]
                else:
                    command += line
                    self.parse_and_run_command(command)
                    command = ''
        if len(command) > 0:
            self.parse_and_run_command(command)

    # Internal

    @staticmethod
    def default_error_handler(env, error):
        print(error.render_full(None), flush=True)


class MainInteractive(MainScript):

    def __init__(self, config_file, testing=False):
        super().__init__(config_file, testing)
        self.tab_completer = marcel.tabcompleter.TabCompleter(self)
        self.reader = None
        self.initialize_reader()  # Sets self.reader
        self.env.reader = self.reader
        self.job_control = marcel.job.JobControl.start(self.env, self.update_namespace)
        # input records the current line of input. If the startup file changes, a ReloadConfigException
        # is thrown. The old Main's input field carries the input to the new Main, allowing the command to
        # execute.
        self.input = None

    # Main

    def shutdown(self, restart=False):
        self.job_control.shutdown()
        self.reader.close()
        return super().shutdown(restart)

    # MainScript

    def execute_command(self, command, pipeline):
        if self.testing or pipeline.first_op().run_in_main_process():
            command.execute(self.env)
        else:
            self.job_control.create_job(command)

    # MainInteractive

    def run(self, print_prompt):
        try:
            while True:
                try:
                    if self.input is None:
                        prompts = self.env.prompts() if print_prompt else (None, None)
                        self.input = self.reader.input(*prompts)
                    # else: Restarted main, and self.input was from the previous incarnation.
                    self.check_for_config_update()
                    self.parse_and_run_command(self.input)
                    self.input = None
                    self.job_control.wait_for_idle_foreground()
                except KeyboardInterrupt:  # ctrl-C
                    print()
        except EOFError:  # ctrl-D
            print()

    # Internal

    def initialize_reader(self):
        readline.set_history_length(HISTORY_LENGTH)
        readline.parse_and_bind('tab: complete')
        readline.parse_and_bind('set editing-mode emacs')
        readline.parse_and_bind('set completion-query-items 50')
        readline.set_pre_input_hook(self.insert_edited_command)
        self.reader = Reader(self.env, self.env.locations.history_path())

    def insert_edited_command(self):
        command = self.reader.take_edited_command()
        if command:
            readline.insert_text(command)
            readline.redisplay()

    def update_namespace(self, child_namespace_changes):
        # pwd requires special handling
        try:
            pwd = child_namespace_changes['PWD']
            self.env.dir_state().cd(pathlib.Path(pwd))
        except KeyError:
            # PWD wasn't changed
            pass
        self.env.namespace.update(child_namespace_changes)

    def check_for_config_update(self):
        config_path = self.env.config_path
        config_mtime = config_path.stat().st_mtime if config_path.exists() else 0
        if config_mtime > self.config_time:
            raise ReloadConfigException()

    @staticmethod
    def default_error_handler(env, error):
        print(error.render_full(env.color_scheme()), flush=True)


class MainAPI(Main):

    def __init__(self, env):
        self.env = env

    # Main

    def shutdown(self, restart=False):
        namespace = self.env.namespace
        if not restart:
            marcel.reservoir.shutdown(self.main_pid)
        return namespace

    # Internal

    @staticmethod
    def default_error_handler(env, error):
        print(error.render_full(None), flush=True)


def fail(message):
    print(message, file=sys.stderr)
    exit(1)


def usage():
    usage = '''marcel [--mpstart fork|spawn|forksever] [SCRIPT]
    
    Run marcel, interactively if a SCRIPT is not specified. Otherwise, run the SCRIPT.
    It should not be necessary to specify --mpstart. fork is the default.
'''
    print(usage, file=sys.stderr)
    sys.exit(1)


# --mpstart: fork/spawn/forkserver. Use fork if not specified
# --config: startup script
def args():
    flags = ('--mpstart', '--config')
    mpstart = 'fork'
    config = None
    script = None
    flag = None
    for arg in sys.argv[1:]:
        if arg in flags:
            flag = arg
        elif arg.startswith('-'):
            usage()
        else:
            if flag is None:
                # arg must be a script name
                script = arg
            else:
                # arg is a flag value
                if flag == '--mpstart':
                    if arg in ('fork', 'spawn', 'forkserver'):
                        mpstart = arg
                    else:
                        usage()
                elif flag == '--config':
                    config = arg
                flag = None
    return mpstart, config, script


def main():
    mpstart, config, script = args()
    multiprocessing.set_start_method(mpstart)
    if script is None:
        # Interactive
        input = None
        while True:
            main = MainInteractive(None)
            main.input = input
            print_prompt = sys.stdin.isatty()
            try:
                main.run(print_prompt)
                break
            except ReloadConfigException:
                input = main.input
                main.shutdown(restart=True)
    else:
        # Script
        main = MainScript(config)
        try:
            with open(script, 'r') as script_file:
                main.run_script(script_file.read())
        except FileNotFoundError:
            fail(f'File not found: {script}')


if __name__ == '__main__':
    main()
