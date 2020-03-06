import atexit
import pathlib
import readline
import sys

import marcel.core
import marcel.env
import marcel.exception
import marcel.globalstate
import marcel.multilinereader
import marcel.op.out
import marcel.parse
import marcel.tabcompleter
from marcel.util import *


HISTORY_FILE = '.marcel_history'
HISTORY_LENGTH = 100


class Command:

    def __init__(self, pipeline):
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


class Reader(marcel.multilinereader.MultiLineReader):

    def __init__(self, global_state, history_file):
        super().__init__(history_file=history_file)
        self.global_state = global_state

    def set_edited_command(self, edited_command):
        self.global_state.edited_command = edited_command

    def take_edited_command(self):
        edited_command = self.global_state.edited_command
        self.global_state.edited_command = None
        return edited_command


class Main:

    def __init__(self):
        config_path = Main.args()
        self.env = marcel.env.Environment(config_path)
        self.tab_completer = marcel.tabcompleter.TabCompleter()
        self.reader = None
        self.initialize_input()
        self.global_state = marcel.globalstate.GlobalState(self.env)
        atexit.register(self.shutdown)

    def run(self):
        try:
            while True:
                try:
                    line = self.reader.input(*self.env.prompts())
                    self.run_command(line)
                except KeyboardInterrupt:  # ctrl-C
                    print()
        except EOFError:  # ctrl-D
            print()

    def run_command(self, line):
        if line:
            try:
                parser = marcel.parse.Parser(line)
                pipeline = parser.parse()
                pipeline.set_global_state(self.global_state)
                Command(pipeline).execute()
            except marcel.exception.KillCommandException as e:
                print(e, file=sys.stderr)

    def initialize_input(self):
        readline.set_pre_input_hook(Main.insert_edited_command)
        readline.set_history_length(HISTORY_LENGTH)
        readline.parse_and_bind('tab: complete')
        readline.parse_and_bind('set editing-mode emacs')
        readline.parse_and_bind('set completion-query-items 50')
        self.reader = Reader(self.env.globals(), self.history_file())

    def history_file(self):
        home = self.env.getenv('HOME')
        return pathlib.Path(home) / HISTORY_FILE

    def shutdown(self):
        self.reader.close()

    @staticmethod
    def args():
        config_path = sys.argv[1] if len(sys.argv) > 1 else None
        return config_path

    def insert_edited_command(self):
        command = self.reader.take_edited_command()
        if command:
            readline.insert_text(command)
            readline.redisplay()


if __name__ == '__main__':
    Main().run()
