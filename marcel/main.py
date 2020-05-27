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

import argparse
import atexit
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


class Console:

    def __init__(self, handle_console_changes):
        self.width = marcel.util.console_width()
        self.handle_console_changes = handle_console_changes

    def check_for_console_changes(self):
        current_width = marcel.util.console_width()
        if self.width != current_width:
            self.width = current_width
            self.handle_console_changes()


class Reader(marcel.multilinereader.MultiLineReader):

    def __init__(self, env, history_file):
        super().__init__(history_file=history_file)
        self.env = env

    def take_edited_command(self):
        edited_command = self.env.edited_command
        self.env.edited_command = None
        return edited_command


class Main:

    MAIN_SLEEP_SEC = 0.1

    def __init__(self, same_process=False):
        # sys.argv sets config_path, dill
        self.config = None
        self.dill = None
        self.parse_args()
        #
        self.same_process = same_process
        try:
            self.env = marcel.env.Environment(self.config)
        except marcel.exception.KillShellException as e:
            print(f'Cannot start marcel: {e}', file=sys.stderr)
            sys.exit(1)
        self.tab_completer = marcel.tabcompleter.TabCompleter(self)
        self.op_modules = marcel.opmodule.import_op_modules(self.env)
        self.env.op_modules = self.op_modules
        self.reader = None
        self.initialize_input()  # Sets self.reader
        self.env.reader = self.reader
        self.job_control = marcel.job.JobControl.start(self.env, self.update_env_vars)
        self.console = Console(self.handle_console_changes)
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
                    self.console.check_for_console_changes()
                    self.run_command(line)
                    while self.job_control.foreground_is_alive():
                        time.sleep(Main.MAIN_SLEEP_SEC)
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
                # Append an out op at the end of pipeline, if there is no output op there already.
                if not pipeline.is_terminal_op('out'):
                    pipeline.append(marcel.opmodule.create_op(self.env, 'out'))
                command = marcel.core.Command(line, pipeline)
                if self.run_immediate(pipeline):
                    command.execute()
                else:
                    self.job_control.create_job(command)
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
        self.job_control.shutdown()
        self.reader.close()

    def insert_edited_command(self):
        command = self.reader.take_edited_command()
        if command:
            readline.insert_text(command)
            readline.redisplay()

    def update_env_vars(self, env_vars_from_child):
        pwd = env_vars_from_child.get('PWD', None)
        assert pwd is not None
        self.env.dir_state().cd(pathlib.Path(pwd))
        dirs = env_vars_from_child.get('DIRS', None)
        assert dirs is not None
        environment = self.env
        environment.setvar('DIRS', dirs)

    def run_immediate(self, pipeline):
        # Job control commands should be run in this process, not a spawned process.
        # Also, if we're testing operator behavior, run in immediate mode.
        return self.same_process or pipeline.first_op.run_in_main_process()

    def handle_console_changes(self):
        for module in self.op_modules.values():
            module.reformat_help()

    def parse_args(self):
        parser = argparse.ArgumentParser(prog='marcel')
        parser.add_argument('config',
                            nargs='?',
                            help='The location of the marcel configuration file, (typically named .marcel.py)')
        parser.add_argument('--dill',
                            nargs='?')
        parser.parse_args(args=sys.argv[1:], namespace=self)
        self.dill = self.dill is None or self.dill not in ('F', 'f', 'False', 'false')

    @staticmethod
    def default_error_handler(env, error):
        print(error.render_full(env.color_scheme()))


if __name__ == '__main__':
    MAIN = Main()
    MAIN.run()
