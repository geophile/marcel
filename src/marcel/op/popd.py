import pathlib

import marcel.core


SUMMARY = '''
Pop the directory stack, and cd to the new top directory.
'''


DETAILS = None


def popd():
    return Popd()


class PopdArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('popd', env, None, SUMMARY, DETAILS)


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
        self.env().dir_state().popd()
        for dir in self.env().dir_state().dirs():
            self.send(dir)

    # Op

    def must_be_first_in_pipeline(self):
        return True
