"""C{map FUNCTION}

Each value from the input sequence is mapped to an output value by FUNCTION.
"""

import marcel.core


def map():
    return Map()


class MapArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('map', global_state)
        self.add_argument('function',
                          type=super().constrained_type(self.check_function, 'not a valid function'))


class Map(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return f'map({marcel.core.Op.function_source(self.function)})'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        self.function.set_op(self)

    def receive(self, x):
        output = self.function() if x is None else self.function(*x)
        self.send(output)
