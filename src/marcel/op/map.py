import marcel.core
import marcel.functionwrapper


SUMMARY = '''
For each item in the input stream, apply a given function and write the result to the output stream.
'''


DETAILS = '''
The {r:function} is applied to each input tuple in the input stream. The components of a tuple
are bound to the {r:function}'s parameters. The output from the function is written to the output stream.
'''


def map(function):
    op = Map()
    op.function = marcel.functionwrapper.FunctionWrapper(function=function)
    return op


class MapArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('map', env, None, SUMMARY, DETAILS)
        self.add_argument('function',
                          type=super().constrained_type(self.check_function, 'Function required'),
                          help='Function to be applied to input items')


class Map(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return f'map({self.function.source()})'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        try:
            self.function.check_validity()
        except marcel.exception.KillCommandException:
            super().check_arg(False, 'function', 'Function either missing or invalid.')
        self.function.set_op(self)

    def receive(self, x):
        output = self.function() if x is None else self.function(*x)
        self.send(output)
