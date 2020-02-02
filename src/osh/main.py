import sys
import readline

from osh.core import Command
from osh.error import CommandKiller
from osh.parse import Parser

PROMPT = '>'


def run_command(line):
    if line:
        try:
            pipeline = Parser(line).parse()
            command = Command(pipeline)
            command.execute()
        except CommandKiller as e:
            print('(%s) %s' % (type(e), e), file=sys.stderr)


def process_input(handle_line):
    readline.parse_and_bind('set editing-mode emacs')
    try:
        while True:
            try:
                line = input('> ')
                handle_line(line)
            except KeyboardInterrupt:  # ctrl-C
                print()
    except EOFError:  # ctrl-D
        print()


def main():
    process_input(run_command)


if __name__ == '__main__':
    main()
