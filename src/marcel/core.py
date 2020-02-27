import argparse

import marcel.exception
import marcel.exception
import marcel.function
import marcel.object.error
from marcel.util import *

Error = marcel.object.error.Error


class ArgParser(argparse.ArgumentParser):

    op_flags = {'gen': ['-p', '--pad']}  # op name -> [flags], for use in tab completion

    def __init__(self, op_name, flags=None):
        super().__init__(prog=op_name)
        ArgParser.op_flags[op_name] = flags

    def exit(self, status=0, message=None):
        raise marcel.exception.KillCommandException(message)

    @staticmethod
    def constrained_type(check_and_convert, message):
        def arg_checker(s):
            try:
                return check_and_convert(s)
            except Exception:
                print_stack()
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
        return marcel.function.Function(s)


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
        raise marcel.exception.KillCommandException(None)

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

    # BaseOp compile-time

    def connect(self, new_op):
        self.next_op = new_op


class Op(BaseOp):
    """Base class for all osh ops, (excluding pipelines).
    """

    def __init__(self):
        BaseOp.__init__(self)

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
        return 'pipeline({})'.format(' | '.join(buffer))

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
        if self.last_op:
            assert self.first_op is not None
            self.last_op.connect(op)
        else:
            self.first_op = op
        self.last_op = op