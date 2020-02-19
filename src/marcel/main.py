import readline
import sys

import marcel.core
import marcel.env
import marcel.exception
import marcel.op.out
import marcel.parse


class Command:

    def __init__(self, pipeline):
        # Append an "out %s" op at the end of pipeline, if there is no output op there already.
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


def run_command(line):
    if line:
        try:
            pipeline = marcel.parse.Parser(line).parse()
            Command(pipeline).execute()
        except marcel.exception.KillCommandException as e:
            print(e, file=sys.stderr)


def process_input(handle_line):
    readline.parse_and_bind('set editing-mode emacs')
    try:
        while True:
            try:
                line = input(marcel.env.ENV.prompt())
                handle_line(line)
            except KeyboardInterrupt:  # ctrl-C
                print()
    except EOFError:  # ctrl-D
        print()


def args():
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    return config_path


def main():
    config_path = args()
    marcel.env.Environment.initialize(config_path)
    process_input(run_command)


if __name__ == '__main__':
    main()
