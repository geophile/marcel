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
        self.remote = False
        self.fork_pipeline = fork_pipeline
        self.threads = []

    # BaseOp

    def doc(self):
        assert False

    def setup_1(self):
        self.fork_pipeline.append(LabelThread())
        # Don't set the LabelThread receiver here. We don't want the receiver cloned,
        # we want all the cloned pipelines connected to the same receiver.
        pass

    def setup_2(self):
        for thread_label in self.thread_labels():
            pipeline_copy = clone(self.fork_pipeline)
            label_thread_op_copy = pipeline_copy.last_op
            assert isinstance(label_thread_op_copy, LabelThread)
            label_thread_op_copy.set_label(thread_label)
            pipeline_copy.setup_1()
            label_thread_op_copy.receiver = self.receiver
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
        labels = None
        if type(self.fork_spec) is int:
            labels = [x for x in range(self.fork_spec)]
        elif type(self.fork_spec) is str:
            cluster = osh.env.ENV.cluster(self.fork_spec)
            if cluster:
                labels = cluster.hosts
                self.remote = True
        if labels is None:
            raise osh.error.CommandKiller('Invalid fork spec @%s' % self.fork_spec)
        return labels
