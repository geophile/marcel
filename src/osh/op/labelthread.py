import osh.core

from osh.util import *


class LabelThread(osh.core.Op):

    def __init__(self):
        super().__init__()
        self.label = None

    def __repr__(self):
        return (('labelthread(label = %s)' % self.label)
                if self.label
                else 'labelthread()')

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        pass

    def receive(self, x):
        assert self.label is not None
        self.send(normalize_output(self.label + x))

    # LabelThread

    def set_label(self, label):
        self.label = (label,)
