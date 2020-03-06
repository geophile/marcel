import threading

import marcel.core
import marcel.exception
import marcel.op.labelthread
import marcel.op.labelthread
import marcel.op.remote
import marcel.op.remote
from marcel.util import *


class PipelineThread(threading.Thread):

    def __init__(self, thread_label, pipeline_copy):
        super().__init__()
        self.thread_label = thread_label
        self.pipeline = pipeline_copy
        self.terminating_exception = None

    def __repr__(self):
        return 'PipelineThread({})'.format(self.thread_label)

    def run(self):
        try:
            self.pipeline.receive(None)
            self.pipeline.receive_complete()
        except Exception as e:
            # print(f'{type(e)}: {e}')
            # print_stack()
            self.terminating_exception = e


class Fork(marcel.core.Op):

    def __init__(self, fork_spec, fork_pipeline):
        super().__init__()
        self.fork_spec = fork_spec
        self.remote = False
        self.fork_pipeline = fork_pipeline
        self.thread_labels = None
        self.threads = []

    def __repr__(self):
        return 'fork({}, {})'.format(self.fork_spec, self.fork_pipeline)

    # BaseOp

    def doc(self):
        assert False

    def setup_1(self):
        self.generate_thread_labels()
        # The fork_pipeline is not a top-level pipeline (executed from main), so it's global state isn't
        # set yet. This op's owning pipeline has its global state by now. So set the fork_pipeline's global state.
        self.fork_pipeline.set_global_state(self.global_state())
        # If the fork pipeline executes locally, then it can be used as is.
        # Otherwise: it needs to be pickled by Remote and sent to the host executing it.
        # The pipeline executing locally is a new one containing just the Remote op.
        if self.remote:
            pipeline = marcel.core.Pipeline()
            pipeline.set_global_state(self.global_state())
            remote_op = marcel.op.remote.Remote(self.fork_pipeline)
            pipeline.append(remote_op)
            self.fork_pipeline = pipeline
        self.fork_pipeline.append(marcel.op.labelthread.LabelThread())
        # Don't set the LabelThread receiver here. We don't want the receiver cloned,
        # we want all the cloned pipelines connected to the same receiver.

    def setup_2(self):
        for thread_label in self.thread_labels:
            pipeline_copy = clone(self.fork_pipeline)
            label_thread_op = pipeline_copy.last_op
            assert isinstance(label_thread_op, marcel.op.labelthread.LabelThread)
            Fork.attach_thread_label(pipeline_copy.first_op, thread_label)  # In case it's Remote
            Fork.attach_thread_label(label_thread_op, thread_label)  # LabelThread
            pipeline_copy.setup_1()
            label_thread_op.receiver = self.receiver
            self.threads.append(PipelineThread(thread_label, pipeline_copy))

    def receive(self, _):
        for thread in self.threads:
            thread.start()
        for thread in self.threads:
            while thread.isAlive():
                try:
                    thread.join(0.1)
                except BaseException as e:
                    # print(f'{type(e)}: {e}')
                    # print_stack()
                    thread.terminating_exception = e
        # Threads may complete normally or fail with a variety of exceptions. Merge them into a single action
        # for the termination of the fork op.
        kill_command = None
        kill_and_resume = None
        ctrl_c = None
        for thread in self.threads:
            e = thread.terminating_exception
            if e:
                if isinstance(e, marcel.exception.KillCommandException):
                    kill_command = e
                if isinstance(e, marcel.exception.KillAndResumeException):
                    kill_and_resume = e
                if isinstance(e, KeyboardInterrupt):
                    ctrl_c = e
        if kill_command:
            raise marcel.exception.KillCommandException(kill_command)
        if ctrl_c:
            raise KeyboardInterrupt()
        if kill_and_resume:
            raise marcel.exception.KillAndResumeException(self, None, str(kill_and_resume))

    # Op

    def arg_parser(self):
        assert False

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    def generate_thread_labels(self):
        if type(self.fork_spec) is int:
            self.thread_labels = [x for x in range(self.fork_spec)]
        elif type(self.fork_spec) is str:
            cluster = self.global_state().env.cluster(self.fork_spec)
            if cluster:
                self.thread_labels = [host for host in cluster.hosts]
                self.remote = True
        if self.thread_labels is None:
            raise marcel.exception.KillCommandException('Invalid fork spec @{}'.format(self.fork_spec))

    @staticmethod
    def attach_thread_label(op, thread_label):
        if isinstance(op, marcel.op.labelthread.LabelThread):
            op.set_label(thread_label)
        elif isinstance(op, marcel.op.remote.Remote):
            op.set_host(thread_label)

