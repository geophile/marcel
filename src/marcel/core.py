import argparse
import sys

import marcel.exception
import marcel.exception
import marcel.functionwrapper
import marcel.helpformatter
import marcel.object.error
import marcel.util

Error = marcel.object.error.Error


class ArgParser(argparse.ArgumentParser):

    op_flags = {}  # op name -> [flags], for use in tab completion
    help_formatter = None

    def __init__(self, op_name, env, flags=None, summary=None, details=None):
        if ArgParser.help_formatter is None:
            ArgParser.help_formatter = marcel.helpformatter.HelpFormatter(env.color_scheme())
        super().__init__(prog=op_name,
                         formatter_class=argparse.RawDescriptionHelpFormatter,
                         description=ArgParser.help_formatter.format(summary),
                         epilog=ArgParser.help_formatter.format(details))
        ArgParser.op_flags[op_name] = flags
        self.env = env

    # ArgumentParser (argparse)

    def parse_args(self, args=None, namespace=None):
        assert isinstance(namespace, Op)
        if args is not None:
            # Replace pipelines by string-valued pipeline references, since argparse operates on strings.
            # Arg processing by each op will convert the pipeline reference back to a pipeline.
            assert marcel.util.is_sequence_except_string(args)
            args_without_pipelines = []
            pipelines = []
            for arg in args:
                if isinstance(arg, Pipeline):
                    pipeline_ref = self.pipeline_reference(len(pipelines))
                    pipelines.append(arg)
                    arg = pipeline_ref
                args_without_pipelines.append(arg)
            args = args_without_pipelines
            namespace.set_pipeline_args(pipelines)
        return super().parse_args(args, namespace)

    def print_help(self, file=None):
        super().print_help(file)

    def exit(self, status=0, message=None):
        if status:
            raise marcel.exception.KillCommandException(message)
        else:
            # Parser is exiting normally, probably because it was run to obtain a help message.
            # We don't want to actually run a command. Proceeding asthe
            # if the command were killed by Ctrl-C escapes correctly.
            raise KeyboardInterrupt()

    # For use by subclasses

    def pipeline_reference(self, pipeline_id):
        return f'pipeline:{pipeline_id}'

    @staticmethod
    def constrained_type(check_and_convert, message):
        def arg_checker(s):
            try:
                return check_and_convert(s)
            except Exception as e:
                raise argparse.ArgumentTypeError(message)
        return arg_checker

    @staticmethod
    def check_non_negative(s):
        n = int(s)
        if n < 0:
            raise ValueError()
        return n

    @staticmethod
    def check_signal_number(s):
        n = int(s)
        if n < 1 or n > 30:
            raise ValueError()
        return n

    def check_function(self, s):
        return marcel.functionwrapper.FunctionWrapper(source=s, globals=self.env.vars())


class BaseOp:
    """Base class for all ops, and for pipelines (sequences of
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
            try:
                self.receive(marcel.util.normalize_output(x))
            except Exception as e:
                self.receive_error(Error(e))

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

    def env(self):
        return self.owner.env

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
        # pipelines is for pipeline args. The actual pipelines are stored here, while a
        # reference to it is substituted into the command's args, for purposes of parsing.
        self.pipelines = None

    def __repr__(self):
        # TODO: Render args
        return self.op_name()

    # Op

    def must_be_first_in_pipeline(self):
        return False

    @classmethod
    def op_name(cls):
        return cls.__name__.lower()

    # API

    def __or__(self, other):
        pipeline = Pipeline()
        pipeline.append(self)
        pipeline.append(other)
        return pipeline

    # For use by this module

    def set_pipeline_args(self, pipelines):
        self.pipelines = pipelines

    # For use by subclasses

    def referenced_pipeline(self, pipeline_ref):
        if not pipeline_ref.startswith('pipeline:'):
            raise marcel.exception.KillCommandException(f'Incorrect pipeline reference: {pipeline_ref}')
        try:
            pipeline_id = int(pipeline_ref[len('pipeline:'):])
            return self.pipelines[pipeline_id]
        except ValueError:
            raise marcel.exception.KillCommandException(f'Incorrect pipeline reference: {pipeline_ref}')

    @staticmethod
    def function_source(function):
        assert isinstance(function, marcel.functionwrapper.FunctionWrapper)
        return function.source()


class Pipeline(BaseOp):

    def __init__(self):
        BaseOp.__init__(self)
        self.env = None
        self.first_op = None
        self.last_op = None

    def __repr__(self):
        buffer = []
        op = self.first_op
        while op:
            buffer.append(str(op))
            op = op.next_op
        return f'pipeline({" | ".join(buffer)})'

    def set_env(self, env):
        self.env = env

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

    # API

    def __or__(self, op):
        self.append(op)
        return self

