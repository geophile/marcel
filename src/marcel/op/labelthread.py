import marcel.core


class LabelThread(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.label = None

    def __repr__(self):
        return (('labelthread(%s)' % self.label)
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

    # The labelthread op only is used on a copy of the pipeline owned by fork. It runs
    # on each thread of the fork, attaching the thread label to output from that thread's
    # execution of the pipeline. We don't want these labelthread instances all calling
    # send_complete (which the default implementation of receive_complete does), because
    # this will result in n+1 calls of the parent pipeline's receiver -- one for each of the
    # n threads, and another from the parent.
    # See bug 4.
    def receive_complete(self):
        pass

    def receive_error(self, error):
        error.set_host(self.label[0])
        self.send(error)

    # LabelThread

    def set_label(self, label):
        self.label = (label,)
