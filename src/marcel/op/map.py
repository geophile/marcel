"""C{map FUNCTION}

Each value from the input sequence is mapped to an output value by FUNCTION.
"""


def map():
    return Map()


class MapArgParser(marcel.osh.core.OshArgParser):

    def __init__(self):
        super().__init__('map')
        self.add_argument('function',
                          type=super().constrained_type(marcel.osh.core.OshArgParser.check_function,
                                                        'not a valid function'))


# map can be used as a generator (function with no args) or
# downstream. That's why receive and execute are both defined.

class Map(marcel.osh.core.Op):

    argparser = MapArgParser()

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return 'map(%s)' % self.function.source

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        self.function.set_op(self)

    def receive(self, x):
        output = self.function() if x is None else self.function(*x)
        self.send(output)

    # Op

    def arg_parser(self):
        return Map.argparser
