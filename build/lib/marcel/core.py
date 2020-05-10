# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import argparse

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
        # For shell usage, a BaseOp's env comes from the pipeline. For the API, the env
        # is set directly on the BaseOp. self._env provides whichever is available when
        # the env is requested.
        self._env = None

    # object

    def __repr__(self):
        assert False

    def __getstate__(self):
        self._env = None
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)

    # BaseOp runtime

    def setup_1(self):
        """setup_1 is run after command-line parsing and before setup_2. It is intended for
        the initialization of op state except for fork pipeline copying.
        """

    def setup_2(self):
        """setup_2 is run after setup_1 and before execution. It is intended for fork pipeline copying.
        """
        pass

    def send(self, x):
        assert not isinstance(x, Error)
        if self.receiver:
            try:
                self.receiver.receive_input(x)
            except marcel.exception.KillAndResumeException as e:
                self.receiver.receive_error(e.error)

    def send_error(self, error):
        assert isinstance(error, Error)
        if self.receiver:
            self.receiver.receive_error(error)

    def send_complete(self):
        """Called by a op class to indicate that there will
        be no more output from the op.
        """
        if self.receiver:
            self.receiver.receive_complete()

    def receive_input(self, x):
        assert not isinstance(x, Error)
        try:
            self.receive(marcel.util.normalize_op_input(x))
        except marcel.exception.KillAndResumeException as e:
            self.receive_error(e.error)

    def receive(self, x):
        """Implemented by a op class to process an input object.
        """
        pass

    def receive_error(self, error):
        assert isinstance(error, Error)
        self.send_error(error)

    def receive_complete(self):
        """Implemented by a op class to do any cleanup required
        after all input has been received.
        """
        self.send_complete()

    def run_local(self):
        return False

    def env(self):
        if self._env is None:
            self._env = self.owner.env
        return self._env

    def set_env(self, env):
        self._env = env

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
        assert False, self.op_name()

    def __iter__(self):
        pipeline = Pipeline()
        pipeline.append(self)
        return PipelineIterator(pipeline)

    # Op

    def non_fatal_error(self, input=None, message=None, error=None):
        assert (message is None) != (error is None)
        if error is None:
            error = Error(f'Running {self} on {input}: {message}')
        self.owner.handle_error(error)
        return error

    def fatal_error(self, input, message):
        error = self.non_fatal_error(input=input, message=message)
        raise marcel.exception.KillAndResumeException(error)

    def must_be_first_in_pipeline(self):
        return False

    @classmethod
    def op_name(cls):
        return cls.__name__.lower()

    # For use by subclasses

    @staticmethod
    def check_arg(ok, arg, message):
        if not ok:
            cause = (f'Incorrect usage of {Op.op_name()}: {message}'
                     if arg is None else
                     f'Incorrect value for {arg} argument of {Op.op_name()}: {message}')
            raise marcel.exception.KillCommandException(cause)

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

    def referenced_pipeline(self, x):
        if isinstance(x, marcel.core.Pipeline):
            # This happens through the API
            return x
        if not x.startswith('pipeline:'):
            raise marcel.exception.KillCommandException(f'Incorrect pipeline reference: {x}')
        try:
            pipeline_id = int(x[len('pipeline:'):])
            return self.pipelines[pipeline_id]
        except ValueError:
            raise marcel.exception.KillCommandException(f'Incorrect pipeline reference: {x}')

    @staticmethod
    def function_source(function):
        assert isinstance(function, marcel.functionwrapper.FunctionWrapper)
        return function.source()


class Pipeline(BaseOp):

    def __init__(self):
        BaseOp.__init__(self)
        self.env = None
        self.error_handler = None
        self.first_op = None
        self.last_op = None

    def __repr__(self):
        buffer = []
        op = self.first_op
        while op:
            buffer.append(str(op))
            op = op.next_op
        return f'pipeline({" | ".join(buffer)})'

    def __iter__(self):
        return PipelineIterator(self)

    def set_env(self, env):
        self.env = env

    def set_error_handler(self, error_handler):
        self.error_handler = error_handler

    def handle_error(self, error):
        self.error_handler(self.env, error)

    # BaseOp

    def setup_1(self):
        assert self.env is not None, f'{self} has no env'
        assert self.error_handler is not None, f'{self} has no error handler'
        op = self.first_op
        while op:
            if op.receiver is None:
                op.receiver = op.next_op
            op.setup_1()
            op = op.next_op
            if isinstance(op, Op):
                if op.must_be_first_in_pipeline():
                    raise marcel.exception.KillCommandException(
                        '%s cannot receive input from a pipe' % op.op_name())

    def setup_2(self):
        op = self.first_op
        while op:
            if op.receiver is None:
                op.receiver = op.next_op
            op.setup_2()
            op = op.next_op

    def receive(self, x):
        self.first_op.receive_input(x)

    def receive_complete(self):
        self.first_op.receive_complete()

    # Pipeline

    def append(self, op):
        op.set_owner(self)
        if self.last_op:
            assert self.first_op is not None
            self.last_op.connect(op)
        else:
            self.first_op = op
        self.last_op = op

    def is_terminal_op(self, op_name):
        return self.last_op.op_name() == op_name

    # API

    def __or__(self, op):
        self.append(op)
        return self


class Command:

    def __init__(self, source, pipeline):
        self.source = source
        self.pipeline = pipeline

    def __repr__(self):
        return str(self.pipeline)

    def execute(self):
        self.pipeline.setup_1()
        self.pipeline.setup_2()
        self.pipeline.receive(None)
        self.pipeline.receive_complete()
        # A Command is executed by a multiprocessing.Process. Need to transmit the Environment's vars
        # relating to the directory, to the parent process, because they may have changed.
        return self.pipeline.env.dir_state().directory_vars()


class PipelineIterator:

    def __init__(self, pipeline):
        env = pipeline.first_op.env()
        # Clone the pipeline because modifications are required.
        pipeline = marcel.util.clone(pipeline)
        assert env is not None  # PipelineIterator should only be used in the API, which sets op env.
        pipeline.set_env(env)
        pipeline.set_error_handler(PipelineIterator.noop_error_handler)
        output = []
        gather_op = env.op_modules['gather'].api_function()(output)
        pipeline.append(gather_op)
        command = Command(None, pipeline)
        try:
            command.execute()
            self.iterator = output.__iter__()
        except marcel.exception.KillCommandException as e:
            marcel.util.print_to_stderr(e)

    def __next__(self):
        return next(self.iterator)

    @staticmethod
    def noop_error_handler(env, error):
        pass
