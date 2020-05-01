import marcel.core
import marcel.functionwrapper


SUMMARY = '''
Tuples in the input stream are filtered using a predicate.
'''


DETAILS = '''
The {r:function} is applied to each input tuple. Tuples for which the {r:function} evalutes to
True are written to the output stream.
'''


def select(function):
    op = Select()
    op.function = marcel.functionwrapper.FunctionWrapper(function=function)
    return op


class SelectArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('select', env, None, SUMMARY, DETAILS)
        self.add_argument('function',
                          type=super().constrained_type(self.check_function, 'not a valid function'),
                          help='Predicate for filtering input tuples')


class Select(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return f'select({self.function.source()})'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        self.function.set_op(self)

    def receive(self, x):
        if self.function(*x):
            self.send(x)
