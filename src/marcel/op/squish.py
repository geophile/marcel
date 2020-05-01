import functools

import marcel.core
import marcel.functionwrapper


SUMMARY = '''
The components of each input tuple are reduced using a given function.
'''


DETAILS = '''
Each input sequence is reduced to a single value, using {r:function} to combine the values.
{r:function} is a binary function that can be used for reduction, e.g. {n:+}, {n:*}, {n:max}, {n:min}.

{b:Example:} If one of the inputs is the list {n:[1, 2, 3, 4]}, then:
{p,wrap=F}
    squish +

will generate {n:10}.

If no {r:function} is provided, then {n:+} is assumed.
'''


def squish(function=None):
    op = Squish()
    op.function = marcel.functionwrapper.FunctionWrapper(function=function)
    return op


class SquishArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('squish', env, None, SUMMARY, DETAILS)
        self.add_argument('function',
                          nargs='?',
                          type=super().constrained_type(self.check_function, 'not a valid function'),
                          help='Reduction function, applied to the components of an input tuple.')


class Squish(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return f'squish({self.function.source()})' if self.function else 'squish()'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        if self.function is None:
            self.function = marcel.functionwrapper.FunctionWrapper(source='+', globals=self.env().vars())
        self.function.set_op(self)

    def receive(self, x):
        self.send(functools.reduce(self.function, x, None))
