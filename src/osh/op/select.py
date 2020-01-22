"""C{select FUNCTION}

C{FUNCTION} is applied to input elements. Elements for which C{FUNCTION}
evaluates to true are emitted as output..
"""

import osh.core


def select():
    return Select()


class SelectArgParser(osh.core.OshArgParser):

    def __init__(self):
        super().__init__('select')
        self.add_argument('function')


class Select(osh.core.Op):

    argparser = SelectArgParser()

    def __init__(self):
        super().__init__()
        self.function = None  # source, from the command line
        self.predicate = None  # The actual function

    def __repr__(self):
        return 'select(%s)' % self.function

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup(self):
        self.predicate = self.source_to_function(self.function)

    def receive(self, x):
        if self.predicate(*x):
            self.send(x)

    # Op

    def arg_parser(self):
        return Select.argparser
