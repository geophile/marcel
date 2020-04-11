import argparse

import marcel.exception
import marcel.exception
import marcel.function
import marcel.object.error
from marcel.util import *

Error = marcel.object.error.Error


class ArgParser(argparse.ArgumentParser):

    op_flags = {}  # op name -> [flags], for use in tab completion

    def __init__(self, op_name, flags=None):
        super().__init__(prog=op_name)
        ArgParser.op_flags[op_name] = flags
        self.global_state = None
        self.pipelines = []

    # ArgumentParser (argparse)

    def parse_args(self, args=None, namespace=None):
        if args is not None:
            # Replace pipelines by string-valued pipeline references, since argparse operates on strings.
            # Arg processing by each op will convert the pipeline reference back to a pipeline.
            assert is_sequence_except_string(args)
            args_without_pipelines = []
            for arg in args:
                if isinstance(arg, Pipeline):
                    pipeline_ref = self.pipeline_reference(len(self.pipelines))
                    self.pipelines.append(arg)
                    arg = pipeline_ref
                args_without_pipelines.append(arg)
            args = args_without_pipelines
        return super().parse_args(args, namespace)

    def exit(self, status=0, message=None):
        raise marcel.exception.KillCommandException(message)

    # ArgParser (marcel)

    def set_global_state(self, global_state):
        self.global_state = global_state

    def print_usage(self, _=None):
        pass

    # For use by subclasses

    def pipeline_reference(self, pipeline_id):
        return f'pipeline:{pipeline_id}'

    @staticmethod
    def constrained_type(check_and_convert, message):
        def arg_checker(s):
            try:
                return check_and_convert(s)
            except Exception:
                raise argparse.ArgumentTypeError(message)
        return arg_checker

    @staticmethod
    def check_non_negative(s):
        n = int(s)
        if n < 0:
            raise ValueError()
        return n

    def check_function(self, s):
        return marcel.function.Function(s, self.global_state.function_namespace())

    def check_pipeline(self, pipeline_ref):
        if not pipeline_ref.startswith('pipeline:'):
            raise marcel.exception.KillCommandException(f'Incorrect pipeline reference: {pipeline_ref}')
        try:
            pipeline_id = int(pipeline_ref[len('pipeline:'):])
            return self.pipelines[pipeline_id]
        except ValueError:
            raise marcel.exception.KillCommandException(f'Incorrect pipeline reference: {pipeline_ref}')


class BaseOp(object):
    """Base class for all osh ops, and for pipelines (sequences of
    ops). Methods of this class implement the op execution and
    inter-op communication. The send* commands are used by subclasses to
    send output to downstream commands. The receive* commands are implemented
    by subclasses to receive and process input from upstream commands.
    """

    def __init__(self):
        # The pipeline to which this op belongs
        self.owner = None
        # The next op in the pipeline, or None if this is the last op in the pipeline.
        self.next_op = None
        # receiver is where op output is sent. Same as next_op unless this is the last
        # op in the pipeline. In which case, the receiver is that of the pipeline containing
        # this one.
        self.receiver = None
        self.command_state = None

    # object

    def __repr__(self):
        assert False

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)

    # BaseOp runtime

    def usage(self, message):
        """Print usage message and exit.
        """
        if message is None:
            message = self.doc()
        print(message, file=sys.stderr)
        raise marcel.exception.KillCommandException(None)

    def doc(self):
        """Print op usage information.
        """
        assert False

    def setup_1(self):
        """setup_1 is run after command-line parsing and before setup_2. It is intended for
        the initialization of op state except for fork pipeline copying.
        """

    def setup_2(self):
        """setup_2 is run after setup_1 and before execution. It is intended for fork pipeline copying.
        """
        pass

    def send(self, x):
        """Called by a op class to send an object of op output to
        the next op.
        """
        if self.receiver:
            try:
                self.receiver.receive_input_or_error(x)
            except marcel.exception.KillAndResumeException as e:
                self.receiver.receive_error(Error(e))

    def send_complete(self):
        """Called by a op class to indicate that there will
        be no more output from the op.
        """
        if self.receiver:
            self.receiver.receive_complete()

    def receive_input_or_error(self, x):
        if isinstance(x, Error):
            self.receive_error(x)
        else:
            self.receive(normalize_output(x))

    def receive(self, x):
        """Implemented by a op class to process an input object.
        """
        pass

    def receive_error(self, error):
        self.send(error)

    def receive_complete(self):
        """Implemented by a op class to do any cleanup required
        after all input has been received.
        """
        self.send_complete()

    def run_local(self):
        return False

    def global_state(self):
        return self.owner.global_state

    # BaseOp compile-time

    def set_owner(self, pipeline):
        self.owner = pipeline

    def connect(self, new_op):
        self.next_op = new_op


class Op(BaseOp):
    """Base class for all ops, (excluding pipelines).
    """

    def __init__(self):
        super().__init__()

    def __repr__(self):
        # TODO: Render args
        return self.op_name()

    # Op

    def arg_parser(self):
        assert False

    def must_be_first_in_pipeline(self):
        return False

    @classmethod
    def op_name(cls):
        return cls.__name__.lower()

    # For use by subclasses

    @staticmethod
    def function_source(function):
        return function.source if isinstance(function, marcel.function.Function) else function


class Pipeline(BaseOp):

    def __init__(self):
        BaseOp.__init__(self)
        self.global_state = None
        self.first_op = None
        self.last_op = None

    def __repr__(self):
        buffer = []
        op = self.first_op
        while op:
            buffer.append(str(op))
            op = op.next_op
        return f'pipeline({" | ".join(buffer)})'

    def set_global_state(self, global_state):
        self.global_state = global_state

    # BaseOp

    def setup_1(self):
        op = self.first_op
        while op:
            if op.receiver is None:
                op.receiver = op.next_op
            op.setup_1()
            op = op.next_op
            if isinstance(op, Op):
                if op.must_be_first_in_pipeline():
                    raise marcel.exception.KillCommandException('%s cannot receive input from a pipe' % op.op_name())

    def setup_2(self):
        op = self.first_op
        while op:
            if op.receiver is None:
                op.receiver = op.next_op
            op.setup_2()
            op = op.next_op

    def receive(self, x):
        try:
            self.first_op.receive(x)
        except marcel.exception.KillAndResumeException as e:
            receiver = self.first_op.receiver
            if receiver:
                receiver.receive_error(Error(e))

    def receive_complete(self):
        self.first_op.receive_complete()

    # Pipeline compile-time

    def append(self, op):
        op.set_owner(self)
        if self.last_op:
            assert self.first_op is not None
            self.last_op.connect(op)
        else:
            self.first_op = op
        self.last_op = op
