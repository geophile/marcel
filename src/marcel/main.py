import atexit
import pathlib
import readline

import marcel.core
import marcel.env
import marcel.exception
import marcel.globalstate
import marcel.job
import marcel.multilinereader
import marcel.op.out
import marcel.parse
import marcel.tabcompleter
from marcel.util import *


HISTORY_FILE = '.marcel_history'
HISTORY_LENGTH = 100


class Command:

    def __init__(self, source, pipeline):
        self.source = source
        self.pipeline = pipeline
        # Append an out op at the end of pipeline, if there is no output op there already.
        if not isinstance(pipeline.last_op, marcel.op.out.Out):
            out = marcel.op.out.Out()
            out.append = False
            out.file = False
            out.csv = False
            pipeline.append(out)

    def __repr__(self):
        return str(self.pipeline)

    def execute(self):
        self.pipeline.setup_1()
        self.pipeline.setup_2()
        self.pipeline.receive(None)
        self.pipeline.receive_complete()
        # A Command is executed by a multiprocessing.Process. Need to transmit the Environment's vars
        # to the parent process, because they may have changed.
        return self.pipeline.global_state.env.vars()


class Reader(marcel.multilinereader.MultiLineReader):

    def __init__(self, global_state, history_file):
        super().__init__(history_file=history_file)
        self.global_state = global_state

    def take_edited_command(self):
        edited_command = self.global_state.edited_command
        self.global_state.edited_command = None
        return edited_command


class Main:

    MAIN_SLEEP_SEC = 0.1

    def __init__(self):
        config_path = Main.args()
        try:
            self.env = marcel.env.Environment(config_path)
        except marcel.exception.KillShellException as e:
            print(f'Cannot start marcel: {e}', file=sys.stderr)
            sys.exit(1)
        self.global_state = marcel.globalstate.GlobalState(self.env)
        self.tab_completer = marcel.tabcompleter.TabCompleter(self.global_state)
        self.reader = None
        self.initialize_input()
        self.job_control = marcel.job.JobControl.start(self.update_env_vars)
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
        except EOFError:  # ctrl-D
            print()

    def run_command(self, line):
        if line:
            try:
                parser = marcel.parse.Parser(line, self.global_state)
                pipeline = parser.parse()
                pipeline.set_global_state(self.global_state)
                command = Command(line, pipeline)
                if Main.is_job_control(line):
                    command.execute()
                else:
                    self.job_control.create_job(command)
            except marcel.exception.KillCommandException as e:
                # print_stack()
                print(e, file=sys.stderr)

    def initialize_input(self):
        readline.set_history_length(HISTORY_LENGTH)
        readline.parse_and_bind('tab: complete')
        readline.parse_and_bind('set editing-mode emacs')
        readline.parse_and_bind('set completion-query-items 50')
        readline.set_pre_input_hook(self.insert_edited_command)
        self.reader = Reader(self.global_state, self.history_file())

    def history_file(self):
        home = self.env.getvar('HOME')
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
        self.env.setvar('PWD', pwd)
        dirs = env_vars_from_child.get('DIRS', None)
        assert dirs is not None
        self.env.setvar('DIRS', dirs)

    @staticmethod
    def is_job_control(line):
        return line.split()[0] in ('bg', 'fg', 'jobs')

    @staticmethod
    def args():
        config_path = sys.argv[1] if len(sys.argv) > 1 else None
        return config_path


if __name__ == '__main__':
    MAIN = Main()
    MAIN.run()
