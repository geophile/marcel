import marcel.core


class LabelThread(marcel.core.Op):

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
        self.send(self.label + x)

    def receive_error(self, error):
        error.set_host(self.label[0])
        self.send(error)

    # LabelThread

    def set_label(self, label):
        self.label = (label,)
