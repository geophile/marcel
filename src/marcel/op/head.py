"""C{head N}

The first N items of the input sequence are passed on as output. All other input
is ignored. N must be an integer.
"""

import marcel.core


def head():
    return Head()


class HeadArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('head', global_state)
        self.add_argument('n',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'))


class Head(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.n = None
        self.received = 0

    def __repr__(self):
        return f'head({self.n})'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        pass

    def receive(self, x):
        self.received += 1
        if self.n >= self.received:
            self.send(x)
