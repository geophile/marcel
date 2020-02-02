import sys
import argparse

import osh.util
import osh.error


class OshArgParser(argparse.ArgumentParser):

    def __init__(self, op_name):
        super().__init__(prog=op_name)

    def exit(self, status=0, message=None):
        # TODO: Use this to avoid SystemExit on argparse error
        super().exit(status, message)

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


class BaseOp(object):
    """Base class for all osh ops, and for pipelines (sequences of
    ops). Methods of this class implement the op execution and
    inter-op communication. The send* commands are used by subclasses to
    send output to downstream commands. The receive* commands are implemented
    by subclasses to receive and process input from upstream commands.
    """

    def __init__(self):
        # The pipeline to which this op belongs.
        self.pipeline = None
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

    # BaseOp runtime

    def usage(self, message):
        """Print usage message and exit.
        """
        if message is None:
            message = self.doc()
        print(message, file=sys.stderr)
        raise osh.error.CommandKiller(None)

    def doc(self):
        """Print op usage information.
        """
        assert False

    def setup(self):
        """Setup is executed just prior to op execution. 
        """
        assert False

    def execute(self):
        """Execute the op.
        """
        assert False

    def send(self, x):
        """Called by a op class to send an object of op output to
        the next op.
        """
        try:
            if self.receiver:
                self.receiver.receive(osh.util.normalize_output(x))
        except osh.error.CommandKiller:
            raise
        except Exception as e:
            osh.error.exception_handler(e, self.receiver, x)

    def send_complete(self):
        """Called by a op class to indicate that there will
        be no more output from the op.
        """
        try:
            if self.receiver:
                self.receiver.receive_complete()
        except osh.error.CommandKiller:
            raise
        except Exception as e:
            osh.error.exception_handler(e, self.receiver, None)

    def receive(self, x):
        """Implemented by a op class to process an input object.
        """
        pass

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
        return self


class Op(BaseOp):
    """Base class for all osh ops, (excluding pipelines).
    """

    # object
    
    def __init__(self):
        BaseOp.__init__(self)
        self.functions = {}  # source -> function

    def __repr__(self):
        # TODO: Render args
        return self.op_name()

    def arg_parser(self):
        assert False

    def source_to_function(self, source):
        function = self.functions.get(source, None)
        if function is None:
            function = Op.symbol_to_function(source)
            if function is None:
                raise osh.error.CommandKiller('Unrecognized function: %s' % source)
        return function

    # For use by subclasses

    thread_label = property(lambda self: self.pipeline.thread_label)

    # For use by this class

    @classmethod
    def op_name(cls):
        return cls.__name__.lower()

    @staticmethod
    def symbol_to_function(symbol):
        if symbol == '+':
            return lambda x, y: x + y
        elif symbol == '*':
            return lambda x, y: x * y
        elif symbol == '^':
            return lambda x, y: x ^ y
        elif symbol == '&':
            return lambda x, y: x & y
        elif symbol == '|':
            return lambda x, y: x | y
        elif symbol == 'and':
            return lambda x, y: x and y
        elif symbol == 'or':
            return lambda x, y: x or y
        elif symbol == 'max':
            return lambda x, y: max(x, y)
        elif symbol == 'min':
            return lambda x, y: min(x, y)
        else:
            return None


class Pipeline(BaseOp):

    def __init__(self):
        BaseOp.__init__(self)
        self.first_op = None
        self.last_op = None
        self.thread_label = None

    def __repr__(self):
        buffer = []
        op = self.first_op
        while op:
            buffer.append(str(op))
            op = op.next_op
        return 'pipeline(%s)' % (' | '.join(buffer))

    # BaseOp

    def setup(self):
        op = self.first_op
        while op:
            if op.receiver is None:
                op.receiver = op.next_op
            op.setup()
            op = op.next_op

    def execute(self):
        try:
            self.first_op.execute()
        except osh.error.CommandKiller:
            raise
        except Exception as e:
            osh.error.exception_handler(e, self.first_op, None)

    def receive(self, x):
        self.first_op.receive(x)

    def receive_complete(self):
        self.first_op.receive_complete()

    # Pipeline compile-time

    def append(self, op):
        if self.last_op:
            self.last_op.connect(op)
        else:
            self.first_op = op
        self.last_op = op
        op.pipeline = self
        return self


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
        try:
            self.pipeline.setup()
            self.pipeline.execute()
            self.pipeline.receive_complete()
        except BaseException as e:
            raise osh.error.CommandKiller(e)
