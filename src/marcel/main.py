import atexit
import pathlib
import readline
import sys

import marcel.core
import marcel.env
import marcel.exception
import marcel.op.out
import marcel.parse
import marcel.tabcompleter


MARCEL_HISTORY_FILE = '.marcel_history'
MARCEL_HISTORY_LENGTH = 100


class Command:

    def __init__(self, pipeline):
        # Append an out op at the end of pipeline, if there is no output op there already.
        if not isinstance(pipeline.last_op, marcel.op.out.Out):
            out = marcel.op.out.Out()
            out.append = False
            out.file = False
            out.csv = False
            pipeline.append(out)
        self.pipeline = pipeline

    def __repr__(self):
        return str(self.pipeline)

    def execute(self):
        self.pipeline.setup_1()
        self.pipeline.setup_2()
        self.pipeline.receive(None)
        self.pipeline.receive_complete()


class Main:

    def __init__(self):
        config_path = Main.args()
        self.env = marcel.env.Environment.initialize(config_path)
        self.tab_completer = marcel.tabcompleter.TabCompleter()
        readline.set_history_length(MARCEL_HISTORY_LENGTH)
        readline.read_history_file(self.history_file())
        readline.parse_and_bind('set editing-mode emacs')
        readline.parse_and_bind('tab: complete')
        atexit.register(lambda: self.shutdown())

    def run(self):
        try:
            while True:
                try:
                    line = input(marcel.env.ENV.prompt())
                    self.run_command(line)
                except KeyboardInterrupt:  # ctrl-C
                    print()
        except EOFError:  # ctrl-D
            print()

    def run_command(self, line):
        if line:
            try:
                parser = marcel.parse.Parser(line)
                self.tab_completer.set_parser(parser)
                pipeline = parser.parse()
                Command(pipeline).execute()
            except marcel.exception.KillCommandException as e:
                print(e, file=sys.stderr)

    def shutdown(self):
        readline.write_history_file(self.history_file())

    def history_file(self):
        home = self.env.getenv('HOME')
        return pathlib.Path(home) / MARCEL_HISTORY_FILE

    @staticmethod
    def args():
        config_path = sys.argv[1] if len(sys.argv) > 1 else None
        return config_path


if __name__ == '__main__':
    Main().run()
