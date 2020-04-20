"""C{pwd}

Output the current directory.
"""

import marcel.core


def pwd():
    return Pwd()


class PwdArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('pwd', global_state)


class Pwd(marcel.core.Op):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return 'pwd()'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        pass

    def receive(self, _):
        self.send(self.global_state().env.pwd())

    # Op

    def must_be_first_in_pipeline(self):
        return True
