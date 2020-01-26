import sys
import subprocess

import osh.core


def escape():
    return Escape()


# This is an unusual OshArgParser subclass. We don't want arg parsing as usual.
# We just want access to the command line args to pass to the shell.
class EscapeArgParser(osh.core.OshArgParser):

    def __init__(self):
        super().__init__('gen')

    def parse_args(self, args=None, namespace=None):
        # The op is passed to namespace, which makes it easy to capture the shell args.
        namespace.shell_args = args


class Escape(osh.core.Op):

    argparser = EscapeArgParser()

    def __init__(self):
        super().__init__()
        self.shell_args = None

    def __repr__(self):
        return 'escape(args=%s)' % str(self.shell_args)

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup(self):
        pass

    def execute(self):
        outcome = subprocess.run(' '.join(self.shell_args),
                                 shell=True,
                                 executable='/bin/bash',
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 universal_newlines=True)
        if outcome.returncode != 0:
            print('Escaped command failed with exit code %s: %s' % (outcome.returncode, ' '.join(self.shell_args)))
            print(outcome.stderr, file=sys.stderr)
        else:
            output = outcome.stdout.split('\n')
            for line in output:
                self.send(line)

    # TODO: Escape not as first op in pipeline. Input stream somehow gets mapped to stdin.

    # Op

    def arg_parser(self):
        return Escape.argparser
