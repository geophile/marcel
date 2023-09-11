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

import sys

import marcel.exception
import marcel.function
import marcel.helpformatter
import marcel.object.error
import marcel.opmodule
import marcel.util

Error = marcel.object.error.Error


def kill_command_on_file_open_error(path, mode, error):
    raise marcel.exception.KillCommandException(f'Unable to open {path} with mode {mode}: {str(error)}')


def kill_and_resume_on_file_open_error(path, mode, error):
    raise marcel.exception.KillAndResumeException(f'Unable to open {path} with mode {mode}: {str(error)}')


class Pipelineable:

    def n_params(self):
        assert False

    def create_pipeline(self, args=None):
        assert False


class AbstractOp(Pipelineable):

    def setup(self, env):
        pass


class Op(AbstractOp):

    def __init__(self):
        super().__init__()
        # The following fields are set and have defined values only during the execution of a pipeline
        # containing this op.
        # The op receiving this op's output
        self.receiver = None
        # The pipeline to which this op belongs
        self.owner = None
        self._count = -1
        # Used temporarily by API, to convey env to PipelineIterator. For the API, a Pipeline is built from
        # a single Op, or from Nodes containing two or more ops. Node construction takes the env, and clears
        # it in its inputs. So by the time an Op or tree of Nodes is turned into a Pipeline, only the root of
        # the tree has an env.
        self.env = None

    def __repr__(self):
        assert False, self.op_name()

    # Pipelineable

    def create_pipeline(self, args=None):
        assert args is None
        pipeline = Pipeline()
        pipeline.append(self)
        return pipeline

    # Op

    def send(self, env, x):
        receiver = self.receiver
        if receiver:
            receiver.receive_input(env, x)

    def send_error(self, error):
        assert isinstance(error, Error)
        if self.receiver:
            self.receiver.receive_error(error)

    def propagate_flush(self, env):
        if self.receiver:
            self.receiver.flush(env)

    def call(self, env, function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            function_input = []
            if args and len(args) > 0:
                function_input.append(str(args))
            if kwargs and len(kwargs) > 0:
                function_input.append(str(kwargs))
            args_description = None if len(function_input) == 0 else ', '.join(function_input)
            self.fatal_error(env, args_description, str(e))

    # This function is performance-critical, so assertions are commented out,
    # and util.wrap_op_input is inlined.
    def receive_input(self, env, x):
        # assert x is not None
        # assert not isinstance(x, Error)
        try:
            env.current_op = self
            self._count += 1
            self.receive(env, x if type(x) in (tuple, list) else (x,))
        except marcel.exception.KillAndResumeException as e:
            self.receive_error(Error(e))

    def pos(self):
        return self._count

    def run(self, env):
        raise marcel.exception.KillCommandException(f'{self.op_name()} cannot be the first operator in a pipeline')

    def receive(self, env, x):
        pass

    def receive_error(self, error):
        assert isinstance(error, Error)
        self.send_error(error)

    def flush(self, env):
        self.propagate_flush(env)

    def cleanup(self):
        pass

    def copy(self):
        copy = self.__class__()
        copy.__dict__.update(self.__dict__)
        return copy

    def non_fatal_error(self, env, input=None, message=None, error=None):
        assert (message is None) != (error is None)
        if error is None:
            error = self.error(input, message)
        self.owner.handle_error(env, error)

    def fatal_error(self, env, input, message):
        error = self.error(input=input, message=message)
        self.owner.handle_error(env, error)
        raise marcel.exception.KillAndResumeException(message)

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

    def __iter__(self):
        env = self.env
        self.env = None
        assert env is not None
        return PipelineIterator(env, self.create_pipeline())


    # arg is a Pipeline, Pipelineable, or a var bound to a pipeline. Deal with all of these possibilities
    # and come up with the pipeline itself.
    @staticmethod
    def pipeline_arg_value(env, arg):
        if type(arg) is marcel.core.Pipeline:
            pipeline = arg
        elif isinstance(arg, marcel.core.Pipelineable):
            pipeline = arg.create_pipeline()
        elif type(arg) is str:  # Presumably a var
            pipeline = env.getvar(arg)
            if type(pipeline) is not marcel.core.Pipeline:
                raise marcel.exception.KillCommandException(
                    f'The variable {arg} is not bound to a pipeline')
        else:
            raise marcel.exception.KillCommandException(
                f'Not a pipeline: {arg}')
        return pipeline

    # Examine the named field, which is a single- or list-valued attr of self.
    # Evaluate any functions found, and then check that the resulting type is
    # one of the given types.
    def eval_function(self, env, field, *types):
        def call(x):
            try:
                if isinstance(x, marcel.function.Function):
                    x = self.call(env, x)
                else:
                    x = x()
            except marcel.exception.KillAndResumeException as e:
                # We are doing setup. Resuming isn't a possibility
                raise marcel.exception.KillCommandException(e)
            if len(types) > 0 and type(x) not in types:
                raise marcel.exception.KillCommandException(
                    f'Type of {self.op_name()}.{field} is {type(x)}, but must be one of {types}')
            return x

        state = self.__dict__
        val = state.get(field, None)
        if callable(val):
            val = call(val)
        elif type(val) in (tuple, list):
            evaled = []
            for x in val:
                if callable(x):
                    x = call(x)
                evaled.append(x)
            val = evaled
        elif type(val) is dict:
            evaled = {}
            for k, v in val.items():
                if callable(v):
                    v = call(v)
                evaled[k] = v
            val = evaled
        return val

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


class Command:

    def __init__(self, source, pipeline):
        self.source = source
        self.pipeline = pipeline

    def __repr__(self):
        return str(self.pipeline)

    def execute(self, env, remote=False):
        depth = env.vars().n_scopes()
        env.clear_changes()
        self.pipeline.setup(env)
        self.pipeline.run(env)
        self.pipeline.flush(env)
        self.pipeline.cleanup()
        # TODO: Deal with exceptions. Pop scopes until depth is reached and reraise.
        assert env.vars().n_scopes() == depth, env.vars().n_scopes()
        # An interactive Command is executed by a multiprocessing.Process (i.e., remotely).
        # Need to transmit the Environment's vars relating to the directory, to the parent
        # process, because they may have changed. This doesn't apply to API usage.
        return env.changes() if remote else None


# Used to represent a function yielding a Node tree (which then yields a Pipeline).
class PipelineFunction(Pipelineable):

    def __init__(self, function):
        if not callable(function):
            raise marcel.exception.KillCommandException(
                f'Should be a function that evaluates to a Pipeline: {function}')
        self.function = function

    def n_params(self):
        return len(self.function.__code__.co_varnames)

    def create_pipeline(self, args=None):
        if args is None:
            args = []
        pipelineable = self.function(*args)
        if not (type(pipelineable) is Node or isinstance(pipelineable, Op)):
            raise marcel.exception.KillCommandException(
                f'Function that should evaluate to a Pipeline evalutes instead to {type(pipelineable)}.')
        return pipelineable.create_pipeline()


class Node(Pipelineable):

    # See comment on Op.env for discussion of env handling

    def __init__(self, left, right):
        self.env = left.env
        left.env = None
        right.env = None
        self.left = left
        self.right = right

    def __or__(self, other):
        assert isinstance(other, Op) or type(other) is Pipeline, type(other)
        return Node(self, other)

    def __iter__(self):
        env = self.env
        self.env = None
        assert env is not None
        pipeline = self.create_pipeline()
        return PipelineIterator(env, pipeline)

    # Pipelineable

    def create_pipeline(self, args=None):
        def visit(op):
            if isinstance(op, Op):
                ops = [op]
            elif type(op) is Pipeline:
                # op will usually be an Op. But the op could represent a Pipeline, e.g.
                #     recent = [select (f: now() - f.mtime < days(1))]
                #     ls | recent
                # In this case, through the CLI, the Pipeline would be wrapped in a runpipeline op. But
                # through the API, op could actually be a Pipeline.
                ops = list(op.ops)
            else:
                assert False, op
            for op in ops:
                # # TODO: Obsolete?
                # # The need to set the owner on the source of the copy is a bit subtle. op might be something that owns
                # # a FunctionWrapper. A FunctionWrapper points to it's op, and error handling requires the op's owner
                # # for error handling. If the owner isn't set prior to the copy, then the copy won't have its
                # # FunctionWrapper's op's owner set.
                # op.set_owner(pipeline)
                pipeline.append(op)

        assert args is None
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


class Pipeline(AbstractOp):

    def __init__(self):
        super().__init__()
        self.error_handler = None
        self.ops = []
        # Parameters declared for a pipeline
        self.params = None
        self.source = None

    def __repr__(self):
        if self.source:
            return self.source
        else:
            params = ', '.join(self.params) if self.params else None
            op_buffer = []
            for op in self.ops:
                op_buffer.append(str(op))
            ops = ' | '.join(op_buffer)
            return f'(| {params}: {ops} |)' if params else f'(| {ops} |)'

    def dump(self, label):
        print(f'{label}: {id(self)}  {self}')
        for op in self.ops:
            print(f'    {id(op)}  {op}')

    def set_error_handler(self, error_handler):
        self.error_handler = error_handler

    def handle_error(self, env, error):
        self.error_handler(env, error)

    # Pipelineable

    def n_params(self):
        return len(self.params) if self.params else 0

    def create_pipeline(self, args=None):
        assert args is None
        return self

    # AbstractOp

    def setup(self, env):
        assert self.error_handler is not None, f'{self} has no error handler'
        prev_op = None
        for op in self.ops:
            if isinstance(op, Op) and op is not self.ops[0] and op.must_be_first_in_pipeline():
                print(f'op: {op}')
                print(f'first op in pipeline: {self.ops[0]}')
                raise marcel.exception.KillCommandException(
                    f'{op.op_name()} cannot receive input from a pipe')
            op.owner = self
            if prev_op:
                prev_op.receiver = op
            prev_op = op
        for op in self.ops:
            op.setup(env)

    # Pipeline

    def run(self, env):
        self.ops[0].run(env)

    def receive(self, env, x):
        op = self.ops[0]
        if x is None:
            op.run(env)
        else:
            op.receive_input(env, x)

    def flush(self, env):
        self.ops[0].flush(env)

    def cleanup(self):
        for op in self.ops:
            op.cleanup()

    def set_parameters(self, parameters):
        if parameters is not None:
            assert len(parameters) > 0
            self.params = parameters

    def parameters(self):
        return self.params

    def copy(self):
        # A pipeline copy contains shallow copies of the ops. This allows an op to make a copy of the pipeline
        # and be sure that the copy doesn't share state or structure (i.e. Op.receiver) with other uses of the
        # "same" pipeline within the same command.
        copy = Pipeline()
        copy.error_handler = self.error_handler
        for op in self.ops:
            copy.append(op.copy())
        copy.params = self.params
        return copy

    def append(self, op):
        self.ops.append(op)

    def prepend(self, op):
        self.ops = [op] + self.ops

    def first_op(self):
        return self.ops[0]

    def last_op(self):
        return self.ops[-1]


class PipelineIterator:

    def __init__(self, env, pipeline):
        # Errors go to output, so no other error handling is needed
        pipeline.set_error_handler(PipelineIterator.noop_error_handler)
        output = []
        gather_op = env.op_modules['gather'].api_function()(output)
        pipeline.append(gather_op)
        command = Command(None, pipeline)
        try:
            command.execute(env)
        except marcel.exception.KillCommandException as e:
            marcel.util.print_to_stderr(e, env)
        finally:
            self.iterator = iter(output)

    def __next__(self):
        return next(self.iterator)

    @staticmethod
    def noop_error_handler(env, error):
        pass


# For the CLI, pipeline syntax is parsed and a Pipeline is created. For the API, a pipeline is a function whose
# body is a marcel expression. PipelineWrapper provides a uniform interface for dealing with pipelines, regardless
# of which interface created is in use.
class PipelineWrapper(object):

    # customize_pipeline takes pipeline as an argument, returns None
    def __init__(self, error_handler, pipeline_arg, customize_pipeline):
        self.error_handler = error_handler
        self.pipeline_arg = pipeline_arg
        self.customize_pipeline = customize_pipeline
        self.pipeline = None

    def __repr__(self):
        return f'PipelineWrapper({self.pipeline_arg})'

    def setup(self, env):
        assert False

    def n_params(self):
        assert False

    def run_pipeline(self, env, args):
        assert False

    def receive(self, env, x):
        self.pipeline.receive(env, x)

    def flush(self, env):
        self.pipeline.flush(env)

    def cleanup(self):
        self.pipeline.cleanup()

    @staticmethod
    def create(error_handler, pipeline_arg, customize_pipeline):
        return (PipelineAPI(error_handler, pipeline_arg, customize_pipeline)
                if type(pipeline_arg) is PipelineFunction
                else PipelineInteractive(error_handler, pipeline_arg, customize_pipeline))


class PipelineInteractive(PipelineWrapper):

    def __init__(self, error_handler, pipeline_arg, customize_pipeline):
        super().__init__(error_handler, pipeline_arg, customize_pipeline)
        self.params = None
        self.scope = None

    def setup(self, env):
        self.pipeline = marcel.core.Op.pipeline_arg_value(env, self.pipeline_arg).copy()
        self.pipeline.set_error_handler(self.error_handler)
        self.pipeline = self.customize_pipeline(env, self.pipeline)
        assert self.pipeline is not None
        self.scope = {}
        self.params = self.pipeline.parameters()
        if self.params is None:
            self.params = []
        for param in self.params:
            self.scope[param] = None

    def n_params(self):
        return self.pipeline.n_params()

    def run_pipeline(self, env, args):
        env.vars().push_scope(self.scope)
        for i in range(len(self.params)):
            env.setvar(self.params[i], args[i])
        try:
            marcel.core.Command(None, self.pipeline).execute(env)
        finally:
            env.vars().pop_scope()

    def prepare_to_receive(self, env):
        self.pipeline.setup(env)


class PipelineAPI(PipelineWrapper):

    def __init__(self, error_handler, pipeline_arg, customize_pipeline):
        super().__init__(error_handler, pipeline_arg, customize_pipeline)
        self.pipeline = None

    def setup(self, env):
        pass

    def n_params(self):
        return self.pipeline_arg.n_params()

    def run_pipeline(self, env, args):
        # Through the API, a pipeline is expressed as a Python function which, when evaluated,
        # yields a pipeline composed of op.core.Nodes. This function is the value of the op's
        # pipeline_arg field. So op.pipeline_arg(*args) evaluates the function (using the current
        # value of the args), and yields the pipeline to execute.
        pipeline = (self.pipeline_arg.create_pipeline(args)
                    if self.n_params() > 0 else
                    self.pipeline_arg.create_pipeline())
        pipeline.set_error_handler(self.error_handler)
        self.pipeline = self.customize_pipeline(env, pipeline)
        marcel.core.Command(None, self.pipeline).execute(env)

    def prepare_to_receive(self, env):
        assert self.n_params() == 0
        pipeline = self.pipeline_arg.create_pipeline()
        pipeline.set_error_handler(self.error_handler)
        self.pipeline = self.customize_pipeline(env, pipeline)
        self.pipeline.setup(env)
