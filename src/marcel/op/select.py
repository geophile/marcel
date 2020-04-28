import marcel.core


SUMMARY = '''
Tuples in the input stream are filtered using a predicate.
'''


DETAILS = '''
The {r:function} is applied to each input tuple. Tuples for which the {r:function} evalutes to
True are written to the output stream.
'''


def select():
    return Select()


class SelectArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('select', env, None, SUMMARY, DETAILS)
        self.add_argument('function',
                          type=super().constrained_type(self.check_function, 'not a valid function'),
                          help='Used to filter input.')


class Select(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return f'select({marcel.core.Op.function_source(self.function)})'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        self.function.set_op(self)

    def receive(self, x):
        if self.function(*x):
            self.send(x)
