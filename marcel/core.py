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
import marcel.function
import marcel.helpformatter
import marcel.object.error
import marcel.util

Error = marcel.object.error.Error


class Pipelineable:

    def create_pipeline(self):
        assert False


class Node(Pipelineable):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __or__(self, other):
        assert isinstance(other, Op) or type(other) is Pipeline, type(other)
        return Node(self, other)

    def __iter__(self):
        pipeline = self.create_pipeline()
        return PipelineIterator(pipeline)

    # Pipelineable

    def create_pipeline(self):
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


class AbstractOp(Pipelineable):

    def setup(self):
        pass

    def set_env(self, env):
        pass


class Op(AbstractOp):

    def __init__(self, env):
        super().__init__()
        self._env = env
        # The following fields are set and have defined values only during the execution of a pipeline
        # containing this op.
        # The op receiving this op's output
        self.receiver = None
        # The pipeline to which this op belongs
        self.owner = None
        # EXPERIMENT
        self._count = -1

    def __repr__(self):
        assert False, self.op_name()

    # Pipelineable

    def create_pipeline(self):
        pipeline = Pipeline()
        pipeline.append(self)
        return pipeline

    # AbstractOp

    def set_env(self, env):
        self._env = env

    # Op

    def send(self, x):
        receiver = self.receiver
        if receiver:
            receiver.receive_input(x)

    def send_error(self, error):
        assert isinstance(error, Error)
        if self.receiver:
            self.receiver.receive_error(error)

    def propagate_flush(self):
        if self.receiver:
            self.receiver.flush()

    def call(self, function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            function_input = []
            if args and len(args) > 0:
                function_input.append(str(args))
            if kwargs and len(kwargs) > 0:
                function_input.append(str(kwargs))
            args_description = None if len(function_input) == 0 else ', '.join(function_input)
            self.fatal_error(args_description, str(e))

    # This function is performance-critical, so assertions are commented out,
    # and util.wrap_op_input is inlined.
    def receive_input(self, x):
        # assert x is not None
        # assert not isinstance(x, Error)
        self._env.current_op = self
        try:
            self._count += 1
            self.receive(x if type(x) in (tuple, list) else
                         (x,))
        except marcel.exception.KillAndResumeException as e:
            self.receive_error(Error(e))

    def pos(self):
        return self._count

    def run(self):
        raise marcel.exception.KillCommandException(f'{self} cannot be the first operator in a pipeline')

    def receive(self, x):
        pass

    def receive_error(self, error):
        assert isinstance(error, Error)
        self.send_error(error)

    def flush(self):
        self.propagate_flush()

    def cleanup(self):
        pass

    def env(self):
        return self._env

    def copy(self):
        copy = self.__class__(self.env())
        copy.__dict__.update(self.__dict__)
        return copy

    def non_fatal_error(self, input=None, message=None, error=None):
        assert (message is None) != (error is None)
        if error is None:
            error = self.error(input, message)
        self.owner.handle_error(error)

    def fatal_error(self, input, message):
        error = self.error(input=input, message=message)
        self.owner.handle_error(error)
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
        return PipelineIterator(self.create_pipeline())

    # For use by subclasses

    def getvar(self, var):
        return self._env.getvar(var)

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
    def eval_function(self, field, *types):
        def call(x):
            try:
                if isinstance(x, marcel.function.Function):
                    x = self.call(x)
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
        val = state[field]
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


class Pipeline(AbstractOp):

    def __init__(self):
        super().__init__()
        self.error_handler = None
        self.ops = []
        # Parameters declared for a pipeline
        self.params = None

    def __repr__(self):
        params = ', '.join(self.params) if self.params else None
        op_buffer = []
        for op in self.ops:
            op_buffer.append(str(op))
        ops = ' | '.join(op_buffer)
        return f'[{params}: {ops}]' if params else f'[{ops}]'

    def dump(self, label):
        print(f'{label}: {id(self)}  {self}')
        for op in self.ops:
            print(f'    {id(op)}  {op}')

    def env(self):
        return self.ops[0].env()

    def set_error_handler(self, error_handler):
        self.error_handler = error_handler

    def handle_error(self, error):
        self.error_handler(self.env(), error)

    # Pipelineable

    def create_pipeline(self):
        return self

    # AbstractOp

    def setup(self):
        assert self.error_handler is not None, f'{self} has no error handler'
        prev_op = None
        for op in self.ops:
            if isinstance(op, Op) and op is not self.ops[0] and op.must_be_first_in_pipeline():
                raise marcel.exception.KillCommandException('%s cannot receive input from a pipe' % op.op_name())
            op.owner = self
            if prev_op:
                prev_op.receiver = op
            prev_op = op
        for op in self.ops:
            op.setup()

    def set_env(self, env):
        for op in self.ops:
            op.set_env(env)

    # Pipeline

    def run(self):
        self.ops[0].run()

    def receive(self, x):
        op = self.ops[0]
        if x is None:
            op.run()
        else:
            op.receive_input(x)

    def flush(self):
        self.ops[0].flush()

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


class Command:

    def __init__(self, env, source, pipeline):
        self.env = env
        self.source = source
        self.pipeline = pipeline

    def __repr__(self):
        return str(self.pipeline)

    def execute(self, api=False):
        depth = self.env.vars().n_scopes()
        self.env.clear_changes()
        self.pipeline.setup()
        self.pipeline.set_env(self.env)
        self.pipeline.run()
        self.pipeline.flush()
        self.pipeline.cleanup()
        # TODO: Deal with exceptions. Pop scopes until depth is reached and reraise.
        assert self.env.vars().n_scopes() == depth, self.env.vars().n_scopes()
        # An interactive Command is executed by a multiprocessing.Process.
        # Need to transmit the Environment's vars relating to the directory, to the parent
        # process, because they may have changed. This doesn't apply to API usage.
        return self.env.changes() if api else None


class PipelineIterator:

    def __init__(self, pipeline):
        env = pipeline.env()
        # Errors go to output, so no other error handling is needed
        pipeline.set_error_handler(PipelineIterator.noop_error_handler)
        output = []
        gather_op = env.op_modules['gather'].api_function()(output)
        pipeline.append(gather_op)
        command = Command(env, None, pipeline)
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
