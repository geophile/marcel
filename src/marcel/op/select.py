"""C{select FUNCTION}

C{FUNCTION} is applied to input elements. Elements for which C{FUNCTION}
evaluates to true are emitted as output..
"""

import marcel.core


def select():
    return Select()


class SelectArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('select', global_state)
        self.add_argument('function',
                          type=super().constrained_type(self.check_function, 'not a valid function'))


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
