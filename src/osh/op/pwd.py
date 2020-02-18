"""C{pwd}

Output the current directory.
"""

import osh.env
import osh.error


def pwd():
    return Pwd()


class PwdArgParser(osh.core.OshArgParser):

    def __init__(self):
        super().__init__('pwd')


class Pwd(osh.core.Op):

    argparser = PwdArgParser()

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return 'pwd()'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        pass

    def receive(self, x):
        assert x is None, x
        self.send(osh.env.ENV.pwd())

    # Op

    def arg_parser(self):
        return Pwd.argparser
