"""C{pwd}

Output the current directory.
"""

import pathlib

import osh.core
import osh.error
from osh.env import ENV


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

    def setup(self):
        pass

    def execute(self):
        self.send(ENV.pwd())

    # Op

    def arg_parser(self):
        return Pwd.argparser
