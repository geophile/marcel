"""C{map FUNCTION}

Each value from the input sequence is mapped to an output value by FUNCTION.
"""

import osh.core


def map():
    return Map()


class MapArgParser(osh.core.OshArgParser):

    def __init__(self):
        super().__init__('map')
        self.add_argument('function')


# map can be used as a generator (function with no args) or
# downstream. That's why receive and execute are both defined.

class Map(osh.core.Op):

    argparser = MapArgParser()

    def __init__(self):
        super().__init__()
        self.function = None  # source, from the command line
        self.f = None  # The actual function

    def __repr__(self):
        return 'map(%s)' % self.function

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup(self):
        self.f = self.source_to_function(self.function)

    def receive(self, x):
        self.send(self.f(*x))

    def execute(self):
        self.send(self.f())

    # Op

    def arg_parser(self):
        return Map.argparser
