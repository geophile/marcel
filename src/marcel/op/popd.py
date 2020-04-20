"""C{popd}

Pop the directory stack (obtainable by the dirs operator), and cd to the new top directory.
"""

import pathlib

import marcel.core


def popd():
    return Popd()


class PopdArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('popd', global_state)


class Popd(marcel.core.Op):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return 'popd()'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        pass

    def receive(self, _):
        self.global_state().env.popd()
        for dir in self.global_state().env.dirs():
            self.send(dir)

    # Op

    def must_be_first_in_pipeline(self):
        return True
