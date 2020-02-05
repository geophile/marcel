import readline

from osh.core import Command
from osh.error import CommandKiller
from osh.parse import Parser
from osh.util import *
import osh.env


def run_command(line):
    if line:
        try:
            pipeline = Parser(line).parse()
            command = Command(pipeline)
            command.execute()
        except CommandKiller as e:
            print(e, file=sys.stderr)


def process_input(handle_line):
    readline.parse_and_bind('set editing-mode emacs')
    try:
        while True:
            try:
                line = input(osh.env.ENV.prompt())
                handle_line(line)
            except KeyboardInterrupt:  # ctrl-C
                print()
    except EOFError:  # ctrl-D
        print()


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    osh.env.Environment.initialize(config_path)
    process_input(run_command)


if __name__ == '__main__':
    main()
