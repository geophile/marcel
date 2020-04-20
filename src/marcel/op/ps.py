"""C{ps [-o|--omit-self]}

Generates a stream of objects of type C{osh.process.Process}.

C{-o} omits the osh process itself from the process list.
"""

import os

import marcel.core
import marcel.object.process


def ps():
    return Ps()


class PsArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('ps', global_state, ['-o', '--omit-self'])
        self.add_argument('-o', '--omit-self',
                          action='store_true')


class Ps(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.omit_self = False

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        pass

    def receive(self, _):
        this_pid = os.getpid()
        for process in marcel.object.process.processes():
            if process.pid != this_pid or not self.omit_self:
                self.send(process)

    # Op

    def must_be_first_in_pipeline(self):
        return True
