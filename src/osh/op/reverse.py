"""C{reverse}

Input objects are sent to the output stream in the opposite order, (last-in first-out).
"""

import osh.core


def reverse():
    return Reverse()


class ReverseArgParser(osh.core.OshArgParser):

    def __init__(self):
        super().__init__('reverse')


class Reverse(osh.core.Op):

    argparser = ReverseArgParser()

    def __init__(self):
        super().__init__()
        self.contents = []

    # BaseOp interface
    
    def doc(self):
        return __doc__

    def setup_1(self):
        pass
    
    def receive(self, x):
        self.contents.append(x)
    
    def receive_complete(self):
        self.contents.reverse()
        for x in self.contents:
            self.send(x)
        self.send_complete()

    # Op

    def arg_parser(self):
        return Reverse.argparser
