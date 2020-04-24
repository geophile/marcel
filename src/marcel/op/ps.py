import os

import marcel.core
import marcel.object.process


SUMMARY = '''
Generate a stream of Process objects, representing running processes.
'''


DETAILS = None


def ps():
    return Ps()


class PsArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('ps', global_state, ['-o', '--omit-self'], SUMMARY, DETAILS)
        self.add_argument('-o', '--omit-self',
                          action='store_true',
                          help='OBSOLETE')


class Ps(marcel.core.Op):

    def __init__(self):
        super().__init__()

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        pass

    def receive(self, _):
        for process in marcel.object.process.processes():
            self.send(process)

    # Op

    def must_be_first_in_pipeline(self):
        return True
