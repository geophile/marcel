"""C{head N}

The first N items of the input sequence are passed on as output. All other input
is ignored. N must be an integer.
"""


def head():
    return Head()


class HeadArgParser(marcel.osh.core.OshArgParser):

    def __init__(self):
        super().__init__('head')
        self.add_argument('n',
                          type=super().constrained_type(marcel.osh.core.OshArgParser.check_non_negative,
                                                        'must be non-negative'))


class Head(marcel.osh.core.Op):

    argparser = HeadArgParser()

    def __init__(self):
        super().__init__()
        self.n = None
        self.received = 0

    def __repr__(self):
        return 'head(n = %s)' % self.n

    # BaseOp interface
    
    def doc(self):
        return __doc__

    def setup_1(self):
        pass

    def receive(self, x):
        self.received += 1
        if self.n >= self.received:
            self.send(x)

    # Op interface

    def arg_parser(self):
        return Head.argparser
