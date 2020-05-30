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

import marcel.exception
import marcel.functionwrapper
import marcel.helpformatter
import marcel.object.error
import marcel.util

Error = marcel.object.error.Error
FunctionWrapper = marcel.functionwrapper.FunctionWrapper


class Pipelineable:

    def create_pipeline(self):
        assert False


class Node(Pipelineable):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __or__(self, other):
        return Node(self, other)

    def __iter__(self):
        return PipelineIterator(self.create_pipeline())

    # Pipelineable

    def create_pipeline(self):
        def visit(op):
            assert isinstance(op, Op)
            # The need to set the owner on the source of the copy is a bit subtle. op might be something that owns
            # a FunctionWrapper. A FunctionWrapper points to it's op, and error handling requires the op's owner
            # for error handling. If the owner isn't set prior to the copy, then the copy won't have its
            # FunctionWrapper's op's owner set.
            op.set_owner(pipeline)
            pipeline.append(op.copy())

        pipeline = Pipeline()
        self.traverse(visit)
        return pipeline

    # Node

    def traverse(self, visit):
        if type(self.left) is Node:
            self.left.traverse(visit)
        else:
            visit(self.left)
        if type(self.right) is Node:
            self.right.traverse(visit)
        else:
            visit(self.right)


# Base class for all ops, and for pipelines. Methods of this class 
# implement the op execution and inter-op communication. The send* 
# commands are used by subclasses to send output to downstream commands. 
# The receive* commands are implemented by subclasses to receive and process 
# input from upstream commands.
class BaseOp(Pipelineable):

    def __init__(self, env):
        assert isinstance(self, Pipeline) or env is not None
        self._env = env
        # The pipeline to which this op belongs
        self.owner = None
        # The next op in the pipeline, or None if this is the last op in the pipeline.
        self.next_op = None
        # receiver is where op output is sent. Same as next_op unless this is the last
        # op in the pipeline. In which case, the receiver is that of the pipeline containing
        # this one.
        self.receiver = None
        self.command_state = None

    def __repr__(self):
        assert False

    # Pipelineable

    def create_pipeline(self):
        assert False

    # BaseOp runtime

    def setup_1(self):
        pass

    def setup_2(self):
        pass

    def send(self, x):
        receiver = self.receiver
        if receiver:
            receiver.receive_input(x)

    def send_error(self, error):
        assert isinstance(error, Error)
        if self.receiver:
            self.receiver.receive_error(error)

    def send_complete(self):
        if self.receiver:
            self.receiver.receive_complete()

    # This function is performance-critical, so the assertion is commented out,
    # and util.normalize_op_input is inlined.
    def receive_input(self, x):
        # assert not isinstance(x, Error)
        try:
            t = type(x)
            self.receive(None if x is None else
                         x if t is tuple else
                         tuple(x) if t is list else
                         (x,))
        except marcel.exception.KillAndResumeException as e:
            self.receive_error(e.error)

    def receive(self, x):
        pass

    def receive_error(self, error):
        assert isinstance(error, Error)
        self.send_error(error)

    def receive_complete(self):
        self.send_complete()

    def run_local(self):
        return False

    def env(self):
        assert self._env is not None
        return self._env

    # BaseOp compile-time

    def set_owner(self, pipeline):
        self.owner = pipeline

    def connect(self, new_op):
        self.next_op = new_op

    def ensure_op(self, x):
        if isinstance(x, Op):
            return x
        elif isinstance(x, Pipeline):
            op = self._env.op_modules['runpipeline'].create_op()
            op.pipeline = x
            return op
        else:
            assert False


# Base class for all ops, excluding pipelines
class Op(BaseOp):

    def __init__(self, env):
        super().__init__(env)

    def __repr__(self):
        assert False, self.op_name()

    def __iter__(self):
        return PipelineIterator(self.create_pipeline())

    # Pipelineable

    def create_pipeline(self):
        pipeline = Pipeline()
        pipeline.append(self.copy())
        return pipeline

    # Op

    def non_fatal_error(self, input=None, message=None, error=None):
        assert (message is None) != (error is None)
        if error is None:
            error = self.error(input, message)
        self.owner.handle_error(error)

    def fatal_error(self, input, message):
        error = self.error(input=input, message=message)
        self.owner.handle_error(error)
        raise marcel.exception.KillAndResumeException(error)

    def must_be_first_in_pipeline(self):
        return False

    def run_in_main_process(self):
        return False

    @classmethod
    def op_name(cls):
        return cls.__name__.lower()

    # API

    def __or__(self, other):
        return Node(self, other)

    def copy(self):
        copy = self.__class__(self.env())
        copy.__dict__.update(self.__dict__)
        return copy

    # For use by subclasses

    def eval_functions(self, *fields):
        state = self.__dict__
        for f in fields:
            val = state[f]
            if callable(val):
                # TODO: DON'T DO THIS: val.set_op(self)
                # TODO: Otherwise, we get resumable error handling (op's error handler) instead of
                # TODO: raising KillCommandException. But this is only correct during setup_1(), not
                # TODO: during receive()? FW error handling is kind of a mess.
                state[f] = val()
            elif type(val) in (tuple, list):
                state[f] = [x() if callable(x) else x for x in val]

    @staticmethod
    def check_arg(ok, arg, message):
        if not ok:
            cause = (f'Incorrect usage of {Op.op_name()}: {message}'
                     if arg is None else
                     f'Incorrect value for {arg} argument of {Op.op_name()}: {message}')
            raise marcel.exception.KillCommandException(cause)

    # For use by this class

    def error(self, input, message):
        return Error(f'Running {self}: {message}'
                     if input is None else
                     f'Running {self} on {input}: {message}')

    @staticmethod
    def function_source(function):
        assert isinstance(function, FunctionWrapper)
        return function.source()


class Pipeline(BaseOp):

    def __init__(self):
        BaseOp.__init__(self, None)
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

    def env(self):
        return self.first_op.env()

    def set_error_handler(self, error_handler):
        self.error_handler = error_handler

    def handle_error(self, error):
        self.error_handler(self.env(), error)

    # Pipelineable

    def create_pipeline(self):
        return marcel.util.copy(self)
    # BaseOp

    def setup_1(self):
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

    def copy(self):
        return marcel.util.copy(self)

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
        return self.pipeline.env().dir_state().directory_vars()


class PipelineIterator:

    def __init__(self, pipeline):
        # Errors go to output, so no other error handling is needed
        pipeline.set_error_handler(PipelineIterator.noop_error_handler)
        output = []
        env = pipeline.env()
        gather_op = env.op_modules['gather'].api_function()(env, output)
        pipeline.append(gather_op)
        command = Command(None, pipeline)
        try:
            command.execute()
        except marcel.exception.KillCommandException as e:
            marcel.util.print_to_stderr(e, env)
        finally:
            self.iterator = iter(output)

    def __next__(self):
        return next(self.iterator)

    @staticmethod
    def noop_error_handler(env, error):
        pass
