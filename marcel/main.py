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
import marcel.multilinereader
import marcel.opmodule
import marcel.parser
import marcel.reservoir
import marcel.tabcompleter
import marcel.util

HISTORY_FILE = '.marcel_history'
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


class SameProcessMode:

    def __init__(self, main, same_process):
        self.main = main
        self.original_same_process = main.same_process
        self.new_same_process = same_process

    def __enter__(self):
        self.main.same_process = self.new_same_process

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.main.same_process = self.original_same_process


class Main:
    MAIN_SLEEP_SEC = 0.1

    def __init__(self, config_file, same_process, old_namespace):
        # sys.argv sets config_path, dill
        self.dill = True
        self.echo = False
        self.main_pid = os.getpid()
        #
        self.same_process = same_process
        try:
            self.env = marcel.env.Environment.new(config_file, old_namespace)
        except marcel.exception.KillShellException as e:
            print(f'Cannot start marcel: {e}', file=sys.stderr)
            sys.exit(1)
        self.tab_completer = marcel.tabcompleter.TabCompleter(self)
        self.op_modules = marcel.opmodule.import_op_modules(self.env)  # op name -> OpModule
        self.env.op_modules = self.op_modules
        self.reader = None
        self.initialize_reader()  # Sets self.reader
        self.input = None
        self.env.reader = self.reader
        self.job_control = marcel.job.JobControl.start(self.env, self.update_namespace)
        self.config_time = time.time()
        self.run_startup()
        self.run_script(marcel.builtin._COMMANDS)
        atexit.register(self.shutdown)

    def __getstate__(self):
        assert False

    def __setstate__(self, state):
        assert False

    def run(self):
        try:
            while True:
                try:
                    if self.input is None:
                        self.input = self.reader.input(*self.env.prompts())
                        if self.echo:
                            print(self.input)
                    # else: Restarted main, and self.line was from the previous incarnation.
                    self.check_for_config_update()
                    self.run_command(self.input)
                    self.input = None
                    self.job_control.wait_for_idle_foreground()
                except KeyboardInterrupt:  # ctrl-C
                    print()
        except EOFError:  # ctrl-D
            print()

    def run_command(self, line):
        if line:
            try:
                parser = marcel.parser.Parser(line, self)
                pipeline = parser.parse()
                pipeline.set_error_handler(Main.default_error_handler)
                # self.run_immediate(pipeline) depends on whether the pipeline has a single op.
                # So check this before tacking on the out op.
                run_immediate = self.run_immediate(pipeline)
                # Append an out op at the end of pipeline, if there is no output op there already.
                if not pipeline.last_op().op_name() == 'out':
                    pipeline.append(marcel.opmodule.create_op(self.env, 'out'))
                command = marcel.core.Command(self.env, line, pipeline)
                if run_immediate:
                    command.execute()
                else:
                    self.job_control.create_job(command)
            except marcel.parser.EmptyCommand:
                pass
            except marcel.exception.KillCommandException as e:
                marcel.util.print_to_stderr(e, self.env)
            except marcel.exception.KillAndResumeException:
                # Error handler printed the error
                pass

    def run_api(self, pipeline):
        command = marcel.core.Command(self.env, None, pipeline)
        try:
            command.execute()
        except marcel.exception.KillCommandException as e:
            marcel.util.print_to_stderr(e, self.env)

    def initialize_reader(self):
        readline.set_history_length(HISTORY_LENGTH)
        readline.parse_and_bind('tab: complete')
        readline.parse_and_bind('set editing-mode emacs')
        readline.parse_and_bind('set completion-query-items 50')
        readline.set_pre_input_hook(self.insert_edited_command)
        self.reader = Reader(self.env, self.history_file())

    def history_file(self):
        environment = self.env
        home = environment.getvar('HOME')
        return pathlib.Path(home) / HISTORY_FILE

    def shutdown(self, restart=False):
        namespace = self.env.namespace
        self.job_control.shutdown()
        self.reader.close()
        if not restart:
            marcel.reservoir.shutdown(self.main_pid)
        return namespace

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

    def run_startup(self):
        run_on_startup = self.env.getvar('RUN_ON_STARTUP')
        if run_on_startup:
            if type(run_on_startup) is str:
                self.run_script(run_on_startup)
            else:
                fail(f'RUN_ON_STARTUP must be a string')
        self.env.compute_config_symbols()

    def run_script(self, script):
        with SameProcessMode(self, True):
            command = ''
            for line in script.split('\n'):
                if len(line.strip()) > 0:
                    if line.endswith('\\'):
                        command += line[:-1]
                    else:
                        command += line
                        self.run_command(command)
                        command = ''
            if len(command) > 0:
                self.run_command(command)

    def check_for_config_update(self):
        config_path = self.env.config_path
        config_mtime = config_path.stat().st_mtime if config_path.exists() else 0
        if config_mtime > self.config_time:
            raise ReloadConfigException()

    @staticmethod
    def default_error_handler(env, error):
        print(error.render_full(env.color_scheme()))

    def run_immediate(self, pipeline):
        return (
                # For the execution of tests and scripts
                self.same_process or
                # Exactly one op in pipeline ...
                pipeline.first_op() is pipeline.last_op() and (
                    # ... and it should run in the main process, or
                    pipeline.first_op().run_in_main_process() or
                    # ... the op is map. I.e. (python expression). This takes care of
                    # side effects we want to keep, e.g. (INTERACTIVE_EXECUTABLES.append(...))
                    pipeline.first_op().op_name() == 'map'))


def fail(message):
    print(message, file=sys.stderr)
    exit(1)


# --dill: bool
# --mpstart: fork/spawn/forkserver. Use fork if not specified
# --echo: bool, indicates whether the command should be echoed. Useful when debugging scripts.
def args():
    flags = ('--dill', '--mpstart', '--echo')
    dill = True
    mpstart = 'fork'
    echo = False
    flag = None
    for arg in sys.argv[1:]:
        if arg in flags:
            flag = arg
            # For a boolean flag, set to True. A different value may be specified by a later arg.
            if flag == '--dill':
                dill = True
            elif flag == '--echo':
                echo = True
        elif arg.startswith('-'):
            fail(f'Unrecognized flag {arg}')
        else:
            # arg is a flag value
            if flag == '--dill':
                dill = arg.lower() in ('t', 'true')
            elif flag == '--mpstart':
                if arg in ('fork', 'spawn', 'forkserver'):
                    mpstart = arg
                else:
                    fail(f'Set --mpstart to fork (default), forkserver, or spawn')
            elif flag == '--echo':
                echo = arg.lower() in ('t', 'true')
            flag = None
    return dill, mpstart, echo


if __name__ == '__main__':
    dill, mpstart, echo = args()
    old_namespace = None
    input = None
    if mpstart is not None:
        multiprocessing.set_start_method(mpstart)
    while True:
        MAIN = Main(None, same_process=False, old_namespace=old_namespace)
        MAIN.input = input
        MAIN.dill = dill
        MAIN.echo = echo
        if os.isatty(sys.stdin.fileno()):
            # Interactive
            try:
                MAIN.run()
                break
            except ReloadConfigException:
                input = MAIN.input
                old_namespace = MAIN.shutdown(restart=True)
                pass
        else:
            # Piped-in script
            MAIN.run_script(sys.stdin.read())
            break
