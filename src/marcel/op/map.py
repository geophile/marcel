import marcel.core


SUMMARY = '''
For each item in the input stream, apply a given function and write the result to the output stream.
'''


DETAILS = '''
The {function} is applied to each input tuple in the input stream. The components of a tuple
are bound to the {function}'s parameters. The output from the function is written to the output stream.
'''


def map():
    return Map()


class MapArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('map', global_state, None, SUMMARY, DETAILS)
        self.add_argument('function',
                          type=super().constrained_type(self.check_function, 'not a valid function'),
                          help='Function to be applied to input items')


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
