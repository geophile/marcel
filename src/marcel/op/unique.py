import marcel.core
import marcel.util


SUMMARY = '''
Write to the output stream all input tuples, but without duplicates.
'''


DETAILS = '''
Input tuples are passed to output, removing duplicates. No output is
generated until the end of the input stream occurs. However, if the
duplicates are known to be consecutive, then {r:-c} allows
output to be generated sooner. Input order is preserved only if {r:-c}
is specified.
'''


def unique(consecutive=False):
    op = Unique()
    op.consecutive = consecutive
    return op


class UniqueArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('unique', env, ['-c', '--consecutive'], SUMMARY, DETAILS)
        self.add_argument('-c', '--consecutive',
                          action='store_true',
                          help='Remove duplicates only when consecutive.')


class Unique(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.consecutive = None
        self.uniquer = None

    # BaseOp

    def setup_1(self):
        self.uniquer = ConsecutiveUniquer(self) if self.consecutive else GeneralUniquer(self)

    def receive(self, x):
        self.uniquer.receive(x)


class Uniquer:

    def receive(self, x):
        assert False


class GeneralUniquer(Uniquer):

    def __init__(self, op):
        self.op = op
        self.unique = set()

    def receive(self, x):
        x = marcel.util.normalize_op_input(x)  # convert list to tuple
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
