import marcel.core
import marcel.env


SUMMARY = '''
Write the marcel version number to the output stream.
'''


DETAILS = None


def version():
    return Version()


class VersionArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('version', env, None, SUMMARY, DETAILS)


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
        self.send(marcel.env.VERSION)

    # Op

    def must_be_first_in_pipeline(self):
        return True
