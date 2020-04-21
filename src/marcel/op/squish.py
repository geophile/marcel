import functools

import marcel.core
import marcel.function


SUMMARY = '''
The components of each input tuple are reduced using a given function.
'''


DETAILS = '''
Each input sequence is reduced to a single value, using {function} to combine the values.
{function} is a binary function that can be used for reduction, e.g. {+}, {*}, {max}, {min}.

b{Example:} If one of the inputs is the list {[1, 2, 3, 4]}, then:

    squish +

will generate {10}.

If no {function} is provided, then {+} is assumed.
'''


def squish():
    return Squish()


class SquishArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('squish', global_state, None, SUMMARY, DETAILS)
        self.add_argument('function',
                          nargs='?',
                          type=super().constrained_type(self.check_function, 'not a valid function'),
                          help='Reduction function, applied to the components of an input tuple.')


class Squish(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return f'squish({self.function})' if self.function else 'squish()'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        if self.function is None:
            self.function = marcel.function.Function('+', self.global_state())
        self.function.set_op(self)

    def receive(self, x):
        self.send(functools.reduce(self.function, x))
