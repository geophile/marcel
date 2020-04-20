"""C{dirs [-c]}

-c|--clear              Clear the directory stack, and place the current directory in it.

The directory stack is output (with or without the C{-c} flag).
"""

import pathlib

import marcel.core


def dirs():
    return Dirs()


class DirsArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('pushd', global_state)
        self.add_argument('-c', '--clear', action='store_true')


class Dirs(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.clear = None

    def __repr__(self):
        return f'dirs(clear={self.clear})'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        pass

    def receive(self, _):
        if self.clear:
            self.global_state().env.reset_dir_stack()
        for dir in self.global_state().env.dirs():
            self.send(dir)

    # Op

    def must_be_first_in_pipeline(self):
        return True
