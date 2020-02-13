import threading

import osh.core
from osh.op.labelthread import LabelThread
from osh.util import clone


class PipelineThread(threading.Thread):

    def __init__(self, thread_label, pipeline_copy):
        super().__init__()
        self.thread_label = thread_label
        self.pipeline = pipeline_copy
        self.terminating_exception = None

    def __repr__(self):
        return 'PipelineThread(%s)' % self.thread_label

    def run(self):
        try:
            self.pipeline.execute()
        except Exception as e:
            self.terminating_exception = e
            osh.util.print_stack()


class Fork(osh.core.Op):

    def __init__(self, fork_spec, fork_pipeline):
        super().__init__()
        self.fork_spec = fork_spec
        self.remote = False
        self.fork_pipeline = fork_pipeline
        self.thread_labels = None
        self.threads = []
        self.generate_thread_labels()

    def __repr__(self):
        return 'fork(%s, %s)' % (self.fork_spec, self.fork_pipeline)

    # BaseOp

    def doc(self):
        assert False

    def setup_1(self):
        # If the fork pipeline executes locally, then it can be used as is.
        # Otherwise: it needs to be pickled by Remote and sent to the host executing it.
        # The pipeline executing locally is a new one containing just the Remote op.
        if self.remote:
            pipeline = osh.core.Pipeline()
            remote_op = osh.op.remote.Remote(self.fork_pipeline)
            pipeline.append(remote_op)
            self.fork_pipeline = pipeline
        self.fork_pipeline.append(LabelThread())
        # Don't set the LabelThread receiver here. We don't want the receiver cloned,
        # we want all the cloned pipelines connected to the same receiver.
        pass

    def setup_2(self):
        for thread_label in self.thread_labels:
            pipeline_copy = clone(self.fork_pipeline)
            label_thread_op = pipeline_copy.last_op
            assert isinstance(label_thread_op, LabelThread)
            Fork.attach_thread_label(pipeline_copy.first_op, thread_label)  # In case it's Remote
            Fork.attach_thread_label(label_thread_op, thread_label)  # LabelThread
            pipeline_copy.setup_1()
            label_thread_op.receiver = self.receiver
            self.threads.append(PipelineThread(thread_label, pipeline_copy))

    def execute(self):
        for thread in self.threads:
            thread.start()
        for thread in self.threads:
            while thread.isAlive():
                thread.join(0.1)
            if thread.terminating_exception:
                osh.error.exception_handler(thread.terminating_exception, self, None, thread)

    # Op

    def arg_parser(self):
        assert False

    # For use by this class

    def generate_thread_labels(self):
        if type(self.fork_spec) is int:
            self.thread_labels = [x for x in range(self.fork_spec)]
        elif type(self.fork_spec) is str:
            cluster = osh.env.ENV.cluster(self.fork_spec)
            if cluster:
                self.thread_labels = [host for host in cluster.hosts]
                self.remote = True
        if self.thread_labels is None:
            raise osh.error.KillCommandException('Invalid fork spec @%s' % self.fork_spec)

    @staticmethod
    def attach_thread_label(op, thread_label):
        if isinstance(op, LabelThread):
            op.set_label(thread_label)
        elif isinstance(op, osh.op.remote.Remote):
            op.set_host(thread_label)

