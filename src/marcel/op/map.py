"""C{map FUNCTION}

Each value from the input sequence is mapped to an output value by FUNCTION.
"""

import marcel.core


def map():
    return Map()


class MapArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('map')
        self.add_argument('function')


# map can be used as a generator (function with no args) or
# downstream. That's why receive and execute are both defined.

class Map(marcel.core.Op):

    argparser = MapArgParser()

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return f'map({self.function.source})'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        self.function = super().create_function(self.function)

    def receive(self, x):
        output = self.function() if x is None else self.function(*x)
        self.send(output)

    # Op

    def arg_parser(self):
        return Map.argparser
