import argparse
import subprocess
import sys

import marcel.core
import marcel.object.error


def bash():
    return Bash()


class BashArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('bash')
        self.add_argument('-i', '--interactive', action='store_true')
        self.add_argument('args',  nargs=argparse.REMAINDER)


class Bash(marcel.core.Op):

    argparser = BashArgParser()

    def __init__(self):
        super().__init__()
        self.interactive = None
        self.args = None

    def __repr__(self):
        return 'bash(args={})'.format(self.args)

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        pass

    def receive(self, _):
        if self.interactive:
            outcome = subprocess.run(' '.join(self.args),
                                     shell=True,
                                     executable='/bin/bash',
                                     universal_newlines=True)
            if outcome.returncode != 0:
                print('Escaped command failed with exit code {}: {}'.format(outcome.returncode, ' '.join(self.args)))
                print(outcome.stderr, file=sys.stderr)
        else:
            outcome = subprocess.run(' '.join(self.args),
                                     shell=True,
                                     executable='/bin/bash',
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     universal_newlines=True)
            # stdout
            for line in Bash.normalize_output(outcome.stdout):
                self.send(line)
            # stderr
            for line in Bash.normalize_output(outcome.stderr):
                self.send(marcel.object.error.Error(line))

    # TODO: bash not as first op in pipeline. Input stream somehow gets mapped to stdin.

    # Op

    def arg_parser(self):
        return Bash.argparser

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    @staticmethod
    def normalize_output(x):
        x = x.split('\n')
        if len(x[-1]) == 0:
            x = x[:-1]
        return x
