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
import pathlib
import readline
import sys
import time

import marcel.core
import marcel.env
import marcel.exception
import marcel.job
import marcel.multilinereader
import marcel.opmodule
import marcel.parser
import marcel.tabcompleter
import marcel.util


HISTORY_FILE = '.marcel_history'
HISTORY_LENGTH = 10000


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


# Used to reload configuration if any config files change.
class ConfigurationMonitor:

    def __init__(self, config_files):
        self.config_time = time.time()
        self.config_files = [pathlib.Path(f) for f in config_files]

    def check_for_config_update(self):
        max_mtime = max([f.stat().st_mtime for f in self.config_files if f.exists()], default=0)
        if max_mtime > self.config_time:
            raise ReloadConfigException()


class Main:

    MAIN_SLEEP_SEC = 0.1

    def __init__(self, config_file, same_process, old_namespace):
        # sys.argv sets config_path, dill
        self.dill = True
        #
        self.same_process = same_process
        try:
            self.env = marcel.env.Environment(config_file, old_namespace)
        except marcel.exception.KillShellException as e:
            print(f'Cannot start marcel: {e}', file=sys.stderr)
            sys.exit(1)
        self.tab_completer = marcel.tabcompleter.TabCompleter(self)
        self.op_modules = marcel.opmodule.import_op_modules(self.env)
        self.env.op_modules = self.op_modules
        self.reader = None
        self.initialize_input()  # Sets self.reader
        self.env.reader = self.reader
        self.job_control = marcel.job.JobControl.start(self.env, self.update_namespace)
        self.config_monitor = ConfigurationMonitor([self.env.config_path])
        self.run_startup()
        atexit.register(self.shutdown)

    def __getstate__(self):
        assert False

    def __setstate__(self, state):
        assert False

    def run(self):
        try:
            while True:
                try:
                    line = self.reader.input(*self.env.prompts())
                    self.run_command(line)
                    while self.job_control.foreground_is_alive():
                        time.sleep(Main.MAIN_SLEEP_SEC)
                except KeyboardInterrupt:  # ctrl-C
                    print()
                self.config_monitor.check_for_config_update()
        except EOFError:  # ctrl-D
            print()

    def run_command(self, line):
        if line:
            try:
                parser = marcel.parser.Parser(line, self)
                pipeline = parser.parse()
                pipeline.set_error_handler(Main.default_error_handler)
                # Append an out op at the end of pipeline, if there is no output op there already.
                if not pipeline.is_terminal_op('out'):
                    pipeline.append(marcel.opmodule.create_op(self.env, 'out'))
                command = marcel.core.Command(line, pipeline)
                if self.run_immediate(pipeline):
                    command.execute()
                else:
                    self.job_control.create_job(command)
            except marcel.parser.EmptyCommand:
                pass
            except marcel.exception.KillCommandException as e:
                marcel.util.print_to_stderr(e, self.env)
            except marcel.exception.KillAndResumeException as e:
                # Error handler printed the error
                pass

    def run_api(self, pipeline):
        command = marcel.core.Command(None, pipeline)
        try:
            command.execute()
        except marcel.exception.KillCommandException as e:
            marcel.util.print_to_stderr(e, self.env)

    def initialize_input(self):
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

    def shutdown(self):
        namespace = self.env.namespace
        self.job_control.shutdown()
        self.reader.close()
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

    def run_immediate(self, pipeline):
        # Job control commands should be run in this process, not a spawned process.
        # Also, if we're testing operator behavior, run in immediate mode.
        return self.same_process or pipeline.first_op.run_in_main_process()

    def run_startup(self):
        run_on_startup = self.env.getvar('RUN_ON_STARTUP')
        if run_on_startup:
            if type(run_on_startup) is str:
                command = ''
                for line in run_on_startup.split('\n'):
                    if len(line.strip()) > 0:
                        command += line
                        if not line.endswith('\\\n'):
                            self.run_command(command)
                            command = ''
                if len(command) > 0:
                    self.run_command(command)
            else:
                fail(f'RUN_ON_STARTUP must be a string')

    @staticmethod
    def default_error_handler(env, error):
        print(error.render_full(env.color_scheme()))


def fail(message):
    print(message, file=sys.stderr)
    exit(1)


# --dill: bool
# --mpstart: fork/spawn/forkserver. Use fork if not specified
def args():
    dill = True
    mpstart = 'fork'
    flag = None
    for arg in sys.argv[1:]:
        if arg == '--dill' or arg == '--mpstart':
            flag = arg
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
    return dill, mpstart


if __name__ == '__main__':
    dill, mpstart = args()
    old_namespace = {}
    if mpstart is not None:
        multiprocessing.set_start_method(mpstart)
    while True:
        MAIN = Main(None, same_process=False, old_namespace=old_namespace)
        MAIN.dill = dill
        try:
            MAIN.run()
            break
        except ReloadConfigException:
            old_namespace = MAIN.shutdown()
            pass
