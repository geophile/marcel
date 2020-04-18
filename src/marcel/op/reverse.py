"""C{reverse}

Input objects are sent to the output stream in the opposite order, (last-in first-out).
"""

import marcel.core


def reverse():
    return Reverse()


class ReverseArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('reverse')


class Reverse(marcel.core.Op):

    argparser = ReverseArgParser()

    def __init__(self):
        super().__init__()
        self.contents = []

    # BaseOp
    
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
