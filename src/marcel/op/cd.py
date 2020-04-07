"""C{cd [DIRECTORY]}

Change the current directory to the given directory. If the DIRECTORY argument is omitted, change the
current directory to the home directory.
"""

import pathlib

import marcel.core


def cd():
    return Cd()


class CdArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('cd')
        self.add_argument('directory',
                          nargs='?',
                          default='~')


class Cd(marcel.core.Op):

    argparser = CdArgParser()

    def __init__(self):
        super().__init__()
        self.directory = None

    def __repr__(self):
        return f'cd({self.directory})'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        self.directory = pathlib.Path(self.directory)

    def receive(self, _):
        self.global_state().env.cd(self.directory)

    # Op

    def arg_parser(self):
        return Cd.argparser

    def must_be_first_in_pipeline(self):
        return True
