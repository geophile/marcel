import pathlib

import marcel.core


SUMMARY = '''
Write the entries in the directory stack to the output stream, top first.
'''


DETAILS = None


def dirs():
    return Dirs()


class DirsArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('pushd', env, ['-c'], SUMMARY, DETAILS)
        self.add_argument('-c', '--clear',
                          action='store_true',
                          help='Clear the directory stack and place the current directory in it.')


class Dirs(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.clear = None

    def __repr__(self):
        return f'dirs(clear={self.clear})'

    # BaseOp

    def setup_1(self):
        pass

    def receive(self, _):
        if self.clear:
            self.env().dir_state().reset_dir_stack()
        for dir in self.env().dir_state().dirs():
            self.send(dir)

    # Op

    def must_be_first_in_pipeline(self):
        return True
