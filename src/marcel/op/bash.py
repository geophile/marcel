import argparse
import shlex
import subprocess
import sys

import marcel.core
import marcel.object.error
from marcel.util import *


def bash():
    return Bash()


class BashArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('bash')
        self.add_argument('-i', '--interactive', action='store_true')
        self.add_argument('args', nargs=argparse.REMAINDER)


class Bash(marcel.core.Op):

    INTERACTIVE_EXECUTABLES = {
        'emacs',
        'less',
        'man',
        'more',
        'psql',
        'vi'
    }
    argparser = BashArgParser()

    def __init__(self):
        super().__init__()
        self.interactive = None
        self.args = None
        self.runner = None
        self.input = []

    def __repr__(self):
        return f'bash(args={self.args})'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        if self.args[0] in Bash.INTERACTIVE_EXECUTABLES:
            self.interactive = True
        self.runner = Interactive(self) if self.interactive else NonInteractive(self)

    def receive(self, x):
        if x is not None:
            if len(x) == 1:
                x = x[0]
            self.input.append(str(x))

    def receive_complete(self):
        self.runner.run()
        self.send_complete()

    # Op

    def arg_parser(self):
        return Bash.argparser


class Escape:

    def __init__(self, op):
        self.op = op

    def run(self):
        assert False

    def command(self):
        return ' '.join([shlex.quote(a) for a in self.op.args])


class NonInteractive(Escape):

    def __init__(self, op):
        super().__init__(op)

    def run(self):
        process = subprocess.Popen(self.command(),
                                   shell=True,
                                   executable='/bin/bash',
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   universal_newlines=True)
        input = NonInteractive.to_string(self.op.input)
        stdout, stderr = process.communicate(input=input)
        process.wait()
        # stdout
        op = self.op
        for line in NonInteractive.normalize_output(stdout):
            op.send(line)
        # stderr
        for line in NonInteractive.normalize_output(stderr):
            op.send(marcel.object.error.Error(line))

    @staticmethod
    def normalize_output(x):
        x = x.split('\n')
        if len(x[-1]) == 0:
            x = x[:-1]
        return x

    @staticmethod
    def to_string(input):
        return '\n'.join(input)


class Interactive(Escape):

    def __init__(self, op):
        super().__init__(op)

    def run(self):
        process = subprocess.Popen(self.command(),
                                   shell=True,
                                   executable='/bin/bash',
                                   universal_newlines=True)
        process.wait()
        if process.returncode != 0:
            print(f'Escaped command failed with exit code {process.returncode}: {" ".join(self.op.args)}')
            print(process.stderr, file=sys.stderr)
1