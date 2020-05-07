import marcel.core


SUMMARY = '''
Write the current directory to the output stream.
'''


DETAILS = None


def pwd():
    return Pwd()


class PwdArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('pwd', env, None, SUMMARY, DETAILS)


class Pwd(marcel.core.Op):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return 'pwd()'

    # BaseOp

    def setup_1(self):
        pass

    def receive(self, _):
        self.send(self.env().dir_state().pwd())

    # Op

    def must_be_first_in_pipeline(self):
        return True
