"""C{squish [FUNCTION]}

Each input sequence is reduced to a single value, using C{FUNCTION} to combine the values.
C{FUNCTION} is a binary function that can be used for reduction, e.g. C{+}, C{*}, C{max}, C{min}.

B{Example}: If one of the inputs is the list C{[1, 2, 3, 4]}, then::

    squish +

will generate C{10} (= C{1 + 2 + 3 + 4}).

If no C{FUNCTION} is provided, then C{+} is assumed.
"""

import functools

import osh.core
import osh.function


def squish():
    return Squish()


class SquishArgParser(osh.core.OshArgParser):

    def __init__(self):
        super().__init__('squish')
        self.add_argument('function',
                          nargs='?',
                          type=super().constrained_type(osh.core.OshArgParser.check_function,
                                                        'not a valid function'))


class Squish(osh.core.Op):

    argparser = SquishArgParser()

    def __init__(self):
        super().__init__()
        self.function = None

    def __repr__(self):
        return 'squish(function = %s' % str(self.function) if self.function else 'squish()'

    # BaseOp interface
    
    def doc(self):
        return __doc__

    def setup_1(self):
        if self.function is None:
            self.function = osh.function.Function('+')
        self.function.set_op(self)

    def receive(self, x):
        self.send(functools.reduce(self.function, x))

    # Op

    def arg_parser(self):
        return Squish.argparser
