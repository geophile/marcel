"""C{unique [-c|--consecutive]}

Input elements are passed to output, removing duplicates. No output is
generated until the end of the input stream occurs. However, if the
duplicates are known to be consecutive, then specifying C{-c} allows
output to be generated sooner. Input order is preserved only if C{-c}
is specified.

"""

import marcel.core
import marcel.util


def unique():
    return Unique()


class UniqueArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('unique', ['-c', '--consecutive'])
        self.add_argument('-c', '--consecutive', action='store_true')


class Unique(marcel.core.Op):

    argparser = UniqueArgParser()

    def __init__(self):
        super().__init__()
        self.consecutive = None
        self.uniquer = None

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        self.uniquer = ConsecutiveUniquer(self) if self.consecutive else GeneralUniquer(self)

    def receive(self, x):
        self.uniquer.receive(x)

    # Op

    def arg_parser(self):
        return Unique.argparser


class Uniquer:

    def receive(self, x):
        assert False


class GeneralUniquer(Uniquer):

    def __init__(self, op):
        self.op = op
        self.unique = set()

    def receive(self, x):
        x = marcel.util.normalize_output(x)  # convert list to tuple
        if x not in self.unique:
            self.unique.add(x)
            self.op.send(x)


class ConsecutiveUniquer(Uniquer):

    def __init__(self, op):
        self.op = op
        self.current = None

    def receive(self, x):
        if self.current != x:
            self.op.send(x)
            self.current = x
