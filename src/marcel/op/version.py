"""version

Generates the version number of this software.
"""

import marcel.core
import marcel.config


def version():
    return Version()


class VersionArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('version', global_state)


class Version(marcel.core.Op):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return 'version()'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        pass

    def receive(self, _):
        self.send(marcel.config.VERSION)

    # Op

    def must_be_first_in_pipeline(self):
        return True
