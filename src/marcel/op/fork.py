import threading

import marcel.core
import marcel.exception
import marcel.op.labelthread
import marcel.op.labelthread
import marcel.op.remote
import marcel.op.remote
import marcel.util


def fork():
    return Fork()


class ForkArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('fork', global_state)
        self.add_argument('fork_spec')
        self.add_argument('fork_pipeline'),


class Fork(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.fork_spec = None
        self.fork_pipeline = None
        self.thread_labels = None
        self.threads = []
        self.impl = None

    def __repr__(self):
        return f'fork({self.fork_spec}, {self.fork_pipeline})'

    # BaseOp

    def doc(self):
        assert False

    def setup_1(self):
        self.fork_pipeline = self.referenced_pipeline(self.fork_pipeline)
        cluster = self.global_state().env.config().clusters.get(self.fork_spec, None)
        self.impl = Remote(self) if cluster else Local(self)
        self.impl.setup_1()

    def setup_2(self):
        self.impl.setup_2()

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
                if isinstance(e, marcel.exception.KillCommandException) or isinstance(e, AssertionError):
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

    def must_be_first_in_pipeline(self):
        return True

    # For use by subclasses

    def generate_thread_labels(self):
        assert False

    # For use by this class

    @staticmethod
    def attach_thread_label(op, thread_label):
        if isinstance(op, marcel.op.labelthread.LabelThread):
            op.set_label(thread_label)
        elif isinstance(op, marcel.op.remote.Remote):
            op.set_host(thread_label)


class ForkImplementation:
    
    def __init__(self, op):
        self.op = op
        
    def setup_1(self):
        self.generate_thread_labels()
        # The fork_pipeline is not a top-level pipeline (executed from main), so its global state isn't
        # set yet. This op's owning pipeline has its global state by now. So set the fork_pipeline's global state.
        op = self.op
        op.fork_pipeline.set_global_state(op.global_state())
        
    def setup_2(self):
        assert False
        
    def generate_thread_labels(self):
        assert False


class Remote(ForkImplementation):

    def __init__(self, op):
        super().__init__(op)

    # BaseOp

    def setup_1(self):
        super().setup_1()
        op = self.op
        remote_pipeline = marcel.core.Pipeline()
        remote_pipeline.set_global_state(op.global_state())
        remote_op = marcel.op.remote.Remote(op.fork_pipeline)
        remote_pipeline.append(remote_op)
        op.fork_pipeline = remote_pipeline
        op.fork_pipeline.append(marcel.op.labelthread.LabelThread())
        # Don't set the LabelThread receiver here. We don't want the receiver cloned,
        # we want all the cloned pipelines connected to the same receiver.

    def setup_2(self):
        op = self.op
        for thread_label in op.thread_labels:
            # Copy the pipeline
            pipeline_copy = marcel.util.clone(op.fork_pipeline)
            # Attach thread label to Remote op.
            remote_op = pipeline_copy.first_op
            assert isinstance(remote_op, marcel.op.remote.Remote)
            remote_op.set_host(thread_label)
            # Attach thread label to LabelThread op.
            label_thread_op = pipeline_copy.last_op
            assert isinstance(label_thread_op, marcel.op.labelthread.LabelThread)
            label_thread_op.set_label(thread_label)
            # DON'T do setup_1 here. The pipeline is going to run remotely, so setup is done remotely.
            # Connect receivers
            remote_op.receiver = label_thread_op
            label_thread_op.receiver = op.receiver
            # Create a thread to run the pipeline copy
            op.threads.append(PipelineThread(thread_label, pipeline_copy))

    # Subclass

    def generate_thread_labels(self):
        op = self.op
        cluster = op.global_state().env.cluster(op.fork_spec)
        if cluster:
            op.thread_labels = [host for host in cluster.hosts]
        else:
            raise marcel.exception.KillCommandException(f'Invalid fork spec @{op.fork_spec}')


class Local(ForkImplementation):

    def __init__(self, op):
        super().__init__(op)
        op.fork_spec = int(op.fork_spec)

    # BaseOp

    def setup_1(self):
        super().setup_1()
        op = self.op
        op.fork_pipeline.append(marcel.op.labelthread.LabelThread())
        # Don't set the LabelThread receiver here. We don't want the receiver cloned,
        # we want all the cloned pipelines connected to the same receiver.

    def setup_2(self):
        op = self.op
        for thread_label in op.thread_labels:
            # Copy the pipeline
            pipeline_copy = marcel.util.clone(op.fork_pipeline)
            pipeline_copy.set_global_state(op.global_state())
            # Attach thread label to LabelThread op.
            label_thread_op = pipeline_copy.last_op
            assert isinstance(label_thread_op, marcel.op.labelthread.LabelThread)
            label_thread_op.set_label(thread_label)
            pipeline_copy.setup_1()
            # Connect LabelThread op to receiver
            label_thread_op.receiver = op.receiver
            # Create a thread to run the pipeline copy
            op.threads.append(PipelineThread(thread_label, pipeline_copy))

    # Subclass

    def generate_thread_labels(self):
        op = self.op
        if type(op.fork_spec) is int:
            op.thread_labels = [x for x in range(op.fork_spec)]
        else:
            raise marcel.exception.KillCommandException(f'Invalid fork spec @{op.fork_spec}')


class PipelineThread(threading.Thread):

    def __init__(self, thread_label, pipeline_copy):
        super().__init__()
        self.thread_label = thread_label
        self.pipeline = pipeline_copy
        self.terminating_exception = None

    def __repr__(self):
        return f'PipelineThread({self.thread_label})'

    def run(self):
        try:
            self.pipeline.receive(None)
            self.pipeline.receive_complete()
        except Exception as e:
            self.terminating_exception = e
