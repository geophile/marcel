import threading

import osh.core
import osh.op
from osh.op.labelthread import LabelThread
from osh.util import clone


class PipelineThread(threading.Thread):

    def __init__(self, thread_label, pipeline_copy):
        super().__init__()
        self.thread_label = thread_label
        self.pipeline = pipeline_copy
        self.pipeline.thread_label = thread_label
        self.terminating_exception = None

    def __repr__(self):
        return 'PipelineThread(%s)' % self.thread_label

    def run(self):
        try:
            self.pipeline.execute()
        except Exception as e:
            self.terminating_exception = e


class Fork(osh.core.Op):

    def __init__(self, fork_spec, fork_pipeline):
        super().__init__()
        self.fork_spec = fork_spec
        self.fork_pipeline = fork_pipeline
        self.threads = []

    # BaseOp

    def doc(self):
        assert False

    def setup(self):
        label_thread_op = LabelThread()
        self.fork_pipeline.append(label_thread_op)
        label_thread_op.receiver = self.receiver
        for thread_label in self.thread_labels():
            pipeline_copy = clone(self.fork_pipeline)
            label_thread_op_copy = pipeline_copy.last_op
            assert isinstance(label_thread_op_copy, LabelThread)
            label_thread_op_copy.set_label(thread_label)
            pipeline_copy.setup()
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

    def thread_labels(self):
        labels = []
        # TODO: Other fork specs
        assert type(self.fork_spec) is int
        for i in range(self.fork_spec):
            labels.append(i)
        return labels
