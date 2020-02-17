import argparse

import osh.error
import osh.function
import osh.env
from osh.util import *


class OshArgParser(argparse.ArgumentParser):

    def __init__(self, op_name):
        super().__init__(prog=op_name)

    def exit(self, status=0, message=None):
        raise osh.error.KillCommandException(message)

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

    @staticmethod
    def check_function(s):
        return osh.function.Function(s)


class BaseOp(object):
    """Base class for all osh ops, and for pipelines (sequences of
    ops). Methods of this class implement the op execution and
    inter-op communication. The send* commands are used by subclasses to
    send output to downstream commands. The receive* commands are implemented
    by subclasses to receive and process input from upstream commands.
    """

    def __init__(self):
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
        raise osh.error.KillCommandException(None)

    def doc(self):
        """Print op usage information.
        """
        assert False

    def setup_1(self):
        """setup_1 is run after command-line parsing and before setup_2. It is intended for
        the initialization of op state except for fork pipeline copying.
        """
        assert False

    def setup_2(self):
        """setup_2 is run after setup_1 and before execution. It is intended for fork pipeline copying.
        """
        pass

    def execute(self):
        """Execute the op.
        """
        assert False

    def send(self, x):
        """Called by a op class to send an object of op output to
        the next op.
        """
        if self.receiver:
            try:
                self.receiver.receive_input_or_error(x)
            except osh.error.KillAndResumeException as e:
                self.receive_input_or_error(OshError(e))

    def send_complete(self):
        """Called by a op class to indicate that there will
        be no more output from the op.
        """
        if self.receiver:
            self.receiver.receive_complete()

    def receive_input_or_error(self, x):
        if isinstance(x, OshError):
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

    # BaseOp compile-time

    def connect(self, new_op):
        self.next_op = new_op


class Op(BaseOp):
    """Base class for all osh ops, (excluding pipelines).
    """

    # object

    def __init__(self):
        BaseOp.__init__(self)

    def __repr__(self):
        # TODO: Render args
        return self.op_name()

    def arg_parser(self):
        assert False

    # For use by this class

    @classmethod
    def op_name(cls):
        return cls.__name__.lower()


class Pipeline(BaseOp):

    def __init__(self):
        BaseOp.__init__(self)
        self.first_op = None
        self.last_op = None

    def __repr__(self):
        buffer = []
        op = self.first_op
        while op:
            buffer.append(str(op))
            op = op.next_op
        return 'pipeline(%s)' % (' | '.join(buffer))

    # BaseOp

    def setup_1(self):
        op = self.first_op
        while op:
            if op.receiver is None:
                op.receiver = op.next_op
            op.setup_1()
            op = op.next_op

    def setup_2(self):
        op = self.first_op
        while op:
            if op.receiver is None:
                op.receiver = op.next_op
            op.setup_2()
            op = op.next_op

    def execute(self):
        self.first_op.execute()

    def receive(self, x):
        self.first_op.receive(x)

    def receive_complete(self):
        self.first_op.receive_complete()

    # Pipeline compile-time

    def append(self, op):
        if self.last_op:
            assert self.first_op is not None
            self.last_op.connect(op)
        else:
            self.first_op = op
        self.last_op = op


class Command:

    def __init__(self, pipeline):
        # Append an "out %s" op at the end of pipeline, if there is no output op there already.
        from osh.op.out import Out
        if not isinstance(pipeline.last_op, Out):
            out = Out()
            out.append = False
            out.file = False
            out.csv = False
            out.format = '%s'
            pipeline.append(out)
        self.pipeline = pipeline

    def __repr__(self):
        return str(self.pipeline)

    def execute(self):
        self.pipeline.setup_1()
        self.pipeline.setup_2()
        self.pipeline.execute()
        self.pipeline.receive_complete()


class OshError:

    def __init__(self, cause):
        self.message = str(cause)
        self.host = None

    def __repr__(self):
        description = ('Error(%s)' % self.message
                       if self.host is None else
                       'Error(%s, %s)' % (self.host, self.message))
        return colorize(description, osh.env.ENV.color_scheme().error)

    def set_host(self, host):
        self.host = host
