import marcel.core
import marcel.object.process


SUMMARY = '''
Generate a stream of Process objects, representing running processes.
'''


DETAILS = None


def ps():
    return Ps()


class PsArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('ps', env, None, SUMMARY, DETAILS)


class Ps(marcel.core.Op):

    def __init__(self):
        super().__init__()

    # BaseOp
    
    def setup_1(self):
        pass

    def receive(self, _):
        for process in marcel.object.process.processes():
            self.send(process)

    # Op

    def must_be_first_in_pipeline(self):
        return True
