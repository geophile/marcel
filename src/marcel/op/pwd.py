"""C{pwd}

Output the current directory.
"""

import marcel.core
import marcel.env


def pwd():
    return Pwd()


class PwdArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('pwd')


class Pwd(marcel.core.Op):

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
        self.send(marcel.env.ENV.pwd())

    # Op

    def arg_parser(self):
        return Pwd.argparser

    def must_be_first_in_pipeline(self):
        return True
