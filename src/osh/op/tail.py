"""C{tail N}

The last N items of the input sequence are passed on as output. All other input
is ignored. N must be an integer.
"""

import osh.core


def tail():
    return Tail()


class TailArgParser(osh.core.OshArgParser):

    def __init__(self):
        super().__init__('tail')
        self.add_argument('n',
                          type=super().constrained_type(osh.core.OshArgParser.check_non_negative,
                                                        'must be non-negative'))


class Tail(osh.core.Op):

    argparser = TailArgParser()

    def __init__(self):
        super().__init__()
        self.n = None
        self.queue = None  # Circular queue
        self.end = 0  # End of the queue

    def __repr__(self):
        return 'tail(n = %s)' % self.n

    # BaseOp interface
    
    def doc(self):
        return __doc__

    def setup(self):
        self.queue = None if self.n == 0 else [None] * self.n

    def receive(self, x):
        if self.queue:
            self.queue[self.end] = x
            self.end = self.next_position(self.end)

    def receive_complete(self):
        if self.queue:
            p = self.end
            count = 0
            while count < self.n:
                x = self.queue[p]
                if x is not None:
                    self.send(x)
                p = self.next_position(p)
                count += 1

    # Op interface

    def arg_parser(self):
        return Tail.argparser

    # For use by this class

    def next_position(self, x):
        return (x + 1) % self.n
