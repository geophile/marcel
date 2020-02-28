import argparse
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
    argparser = BashArgParser()

    def __init__(self):
        super().__init__()
        self.interactive = None
        self.args = None
        self.runner = None
        self.input = []

    def __repr__(self):
        return 'bash(args={})'.format(self.args)

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        self.runner = Interactive(self) if self.interactive else NonInteractive(self)

    def receive(self, x):
        self.input.append(x)

    def receive_complete(self):
        self.runner.run()

    # Op

    def arg_parser(self):
        return Bash.argparser


class NonInteractive:

    def __init__(self, op):
        self.op = op

    def run(self):
        command = ' '.join(self.op.args)
        process = subprocess.Popen(command,
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
        #
        op.send_complete()

    @staticmethod
    def normalize_output(x):
        x = x.split('\n')
        if len(x[-1]) == 0:
            x = x[:-1]
        return x

    @staticmethod
    def to_string(input):
        buffer = []
        for t in input:
            if is_sequence_except_string(t):
                t = t[0]
            buffer.append(str(t))
        return '\n'.join(buffer)


class Interactive:

    def __init__(self, op):
        self.op = op

    def run(self):
        process = subprocess.Popen(self.op.args,
                                   shell=True,
                                   executable='/bin/bash',
                                   universal_newlines=True)
        process.wait()
        if process.returncode != 0:
            print('Escaped command failed with exit code {}: {}'.format(process.returncode, ' '.join(self.op.args)))
            print(process.stderr, file=sys.stderr)
        self.op.send_complete()
