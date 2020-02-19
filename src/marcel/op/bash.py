import argparse
import subprocess
import sys


def bash():
    return Bash()


class BashArgParser(marcel.osh.core.OshArgParser):

    def __init__(self):
        super().__init__('bash')
        self.add_argument('args',  nargs=argparse.REMAINDER)


class Bash(marcel.osh.core.Op):

    argparser = BashArgParser()

    def __init__(self):
        super().__init__()
        self.args = None

    def __repr__(self):
        return 'bash(args=%s)' % str(self.args)

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        pass

    def receive(self, x):
        assert x is None, x
        outcome = subprocess.run(' '.join(self.args),
                                 shell=True,
                                 executable='/bin/bash',
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 universal_newlines=True)
        if outcome.returncode != 0:
            print('Escaped command failed with exit code %s: %s' % (outcome.returncode, ' '.join(self.args)))
            print(outcome.stderr, file=sys.stderr)
        else:
            output = outcome.stdout.split('\n')
            if len(output[-1]) == 0:
                output = output[:-1]
            for line in output:
                self.send(line)

    # TODO: bash not as first op in pipeline. Input stream somehow gets mapped to stdin.

    # Op

    def arg_parser(self):
        return Bash.argparser
