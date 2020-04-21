import pathlib

import marcel.core


SUMMARY = '''
Change the current directory to the given directory.
'''


DETAILS = '''
If {directory} is omitted, then change the current directory to the home directory.
'''


def cd():
    return Cd()


class CdArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('cd', global_state, None, SUMMARY, DETAILS)
        self.add_argument('directory',
                          nargs='?',
                          default='~',
                          help='New current directory')


class Cd(marcel.core.Op):

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

    def must_be_first_in_pipeline(self):
        return True
