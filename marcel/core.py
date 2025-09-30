# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

from enum import Enum, auto

import marcel.env
import marcel.exception
import marcel.function
import marcel.helpformatter
import marcel.object.error
import marcel.opmodule
import marcel.util

Error = marcel.object.error.Error


def convert_to_pipeline(env, x):
    if isinstance(x, str):
        x = marcel.util.string_value(x)
    return x if isinstance(x, marcel.core.Pipeline) else marcel.core.Pipeline.create(env, x)


class AbstractOp(object):

    def setup(self, env):
        pass


class Op(AbstractOp):

    def __init__(self):
        super().__init__()
        # The following fields are set and have defined values only during the execution of a pipelines
        # containing this op.
        # The op receiving this op's output
        self.receiver = None
        # The pipelines to which this op belongs
        self.owner = None
        # Supports pos()
        self._count = -1

    def __repr__(self):
        assert False, self.op_name()

    # AbstractOp

    def setup(self, env):
        pass

    # Op

    def send(self, env, x):
        if env.trace.is_enabled():
            env.trace.write(self, 'RUN', str(x))
        receiver = self.receiver
        if receiver:
            receiver.receive_input(env, x)

    def send_error(self, env, error):
        if env.trace.is_enabled():
            env.trace.write(self, error)
        assert isinstance(error, Error)
        if self.receiver:
            self.receiver.receive_error(env, error)

    def propagate_flush(self, env):
        if self.receiver:
            self.receiver.flush(env)

    def customize_pipelines(self, env):
        pass

    # For use by subclasses

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
        # assert f is not None
        # assert not isinstance(f, Error)
        try:
            env.current_op = self
            self._count += 1
            self.receive(env, x if type(x) in (tuple, list) else (x,))
        except marcel.exception.KillAndResumeException as e:
            pass

    def pos(self):
        return self._count

    def run(self, env):
        if self.must_not_be_first_in_pipeline():
            raise marcel.exception.KillCommandException(f'{self.op_name()} cannot be the first operator in a pipeline')
        else:
            self.receive(env, [])

    def receive(self, env, x):
        # This op has no receive, so run must be what's needed, e.g. gen in:
        #     case (...) (| gen ... |) (| ... |)
        self.run(env)

    def receive_error(self, env, error):
        assert isinstance(error, Error)
        self.send_error(env, error)

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
        self.send_error(env, error)

    def fatal_error(self, env, input, message):
        error = self.error(input=input, message=message)
        try:
            self.send_error(env, error)
        except:
            # If the error occurred during setup, then send_error can't work
            pass
        finally:
            raise marcel.exception.KillAndResumeException(message)

    def must_be_first_in_pipeline(self):
        return False

    def must_not_be_first_in_pipeline(self):
        return False

    def run_in_main_process(self):
        return False

    @classmethod
    def op_name(cls):
        return cls.__name__.lower()

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
            except Exception as e:
                # We are doing setup. Resuming isn't a possibility
                raise marcel.exception.KillCommandException(e)
            if len(types) > 0 and not marcel.util.one_of(x, types):
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
        assert isinstance(pipeline, Pipeline)
        self.source = source
        self.pipeline = pipeline

    def __repr__(self):
        return f'({type(self.pipeline)}) {self.pipeline}'

    def execute(self, env, remote=False):
        with env.check_nesting():
            # Clear env changes iff remote.vars_written
            # - remote = True: This is top-level execution, on behalf of a Job.
            # - remote = False: Either top-level and not a Job, or nested execution. Either way,
            #       changes aren't tracked or needed.
            # Bug 270 was occurring because execution of a command's pipeline was clearing changes
            # relevant to the top-level command.
            if remote:
                env.clear_changes()
            self.pipeline.run_pipeline(env, {})
        # An interactive Command is executed by a multiprocessing.Process (i.e., remotely).
        # Need to transmit the Environment's vars relating to the directory, to the parent
        # process, because they may have changed. This doesn't apply to API usage.
        return env.changes() if remote else None


# Used to represent a function yielding an OpList (which then yields a Pipeline).
class PipelineFunction(object):

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
        op_list = self.function(*args)
        assert type(op_list) is OpList, op_list
        return op_list.create_pipeline()


# For use by API
class OpList(object):

    def __init__(self, env, op):
        # The API constructs a pipelines by or-ing together the objects returned by marcel.api._generate_op.
        # This class is written to work as both the object returned for each op, and the accumulator. E.g.
        # map() | select() | red()
        # 1. map() returns an OpList with op = map()
        # 2. select() returns an OpList with op = select()
        # 3. These OpLists are or-ed, returning an OpList placing map() and select() into ops.
        # 4. Then red() yields an OpList with op set to red(), and that is or-ed appending to OpList.ops from step 3.
        self.env = env
        self.op = op
        self.ops = None

    def __or__(self, other):
        if self.ops is None:
            # self must be the first op of a pipelines
            self.ops = [self.op]
            self.op = None
        # Append ops from other. There could be one or more than one
        assert (other.op is None) != (other.ops is None)
        if other.op:
            self.ops.append(other.op)
        else:
            self.ops.extend(other.ops)
        return self

    def __iter__(self):
        return PipelineIterator(self.env, self.create_executable_pipeline())

    def create_executable_pipeline(self, args=None):
        assert args is None
        assert not (self.op is not None and self.ops is not None)
        # self.op and ops could both be None. E.g., this happens with upload, which starts with an empty pipeline.
        pipeline = PipelineExecutable()
        if self.op is not None:
            pipeline.append(self.op)
        elif self.ops is not None:
            for op in self.ops:
                pipeline.append(op)
        return pipeline


class PipelineExecutable(AbstractOp):

    def __init__(self):
        super().__init__()
        self.ops = []
        # Parameters declared for a pipelines
        self.params = tuple()
        self.source = None

    def __repr__(self):
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

    # AbstractOp

    def setup(self, env):
        prev_op = None
        for op in self.ops:
            if isinstance(op, Op) and op is not self.ops[0] and op.must_be_first_in_pipeline():
                raise marcel.exception.KillCommandException(
                    f'{op.op_name()} cannot receive input from a pipe')
            op.owner = self
            if prev_op:
                prev_op.receiver = op
            prev_op = op
        for op in self.ops:
            if env.trace.is_enabled():
                env.trace.write(op, 'SETUP')
            op.setup(env)
        for op in self.ops:
            op.customize_pipelines(env)

    # PipelineExecutable lifecycle

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
        self.state = PipelineMarcel.State.IDLE

    # PipelineExecutable editing

    def set_parameters(self, parameters):
        assert type(parameters) in (tuple, list)
        self.params = tuple(parameters)

    def parameters(self):
        return self.params

    def copy(self):
        # A pipeline's copy contains shallow copies of the ops. This allows an op to make a copy of the pipelines
        # and be sure that the copy doesn't share state or structure (i.e. Op.receiver) with other uses of the
        # "same" pipelines within the same command.
        copy = PipelineExecutable()
        copy.params = self.params
        copy.source = self.source
        for op in self.ops:
            copy.append(op.copy())
        return copy

    def append(self, op):
        self.ops.append(op)

    def append_immutable(self, op):
        copy = PipelineExecutable()
        copy.params = self.params
        copy.source = self.source
        copy.ops = self.ops.copy()
        if len(copy.ops) > 0:
            current_last_op = copy.ops[-1]
            current_last_op.receiver = op
        copy.ops.append(op)
        return copy

    def first_op(self):
        return self.ops[0]

    def last_op(self):
        return self.ops[-1]

    def n_params(self):
        return len(self.params)

    def create_pipeline(self, args=None):
        assert args is None
        return self


class PipelineIterator:

    def __init__(self, env, pipeline):
        output = []
        gather_op = env.op_modules['gather'].api_function()(output)
        pipeline.append(gather_op)
        command = Command(None, pipeline)
        try:
            command.execute(env)
        except marcel.exception.KillCommandException as e:
            marcel.util.print_to_stderr(env, e)
        finally:
            self.iterator = iter(output)

    def __next__(self):
        return next(self.iterator)


# There are a few kinds of pipelines:
# - PipelineExecutable: Created directly by Parser, and used for execution of pipelines.
# - OpList: Constructed by marcel.api, can be used to generate PipelineExecutable.
# - function evaluated to OpList: Also constructed by marcel.api, for parameterized pipelines.
# - PipelineFunction: Wrapper around function that evaluates to OpList.
# Pipeline provides a uniform interface to all of these. There are subclasses (PipelineMarcel, PipelinePython)
# corresponding to script/interactive vs. API usage. E.g. PipelineMarcel pipelines need parameters and scopes
# explicitly managed while PipelinePython pipelines do not.
class Pipeline(object):

    # object

    def __init__(self, executable, customize_pipeline):
        # executable is None if we're using the API, and the pipeline is specified as a lambda.
        assert executable is None or isinstance(executable, PipelineExecutable), type(executable)
        self.executable = executable
        self.customize_pipeline = customize_pipeline
        self.state = PipelineMarcel.State.IDLE

    def __repr__(self):
        return f'Pipeline({self.executable})'

    # Pipeline - execution

    def setup(self, env):
        assert False

    def receive(self, env, x):
        self.executable.receive(env, x)

    def flush(self, env):
        self.executable.flush(env)

    def cleanup(self):
        self.executable.cleanup()

    def parameters(self):
        return self.executable.parameters()

    def run_pipeline(self, env, bindings):
        assert False

    # Pipeline - construction

    def copy(self):
        assert False

    def append(self, op):
        self.executable.append(op)

    def append_immutable(self, op):
        self.executable.append_immutable(op)

    def route_output(self, receiver):
        assert False

    def ensure_terminal_write(self, env):
        if not self.executable.last_op().op_name() == 'write':
            self.executable.append(marcel.opmodule.create_op(env, 'write'))

    # Pipeline - transmission

    def pickle(self, pickler):
        pickler.dump(self.executable)

    @staticmethod
    def create(env, pipeline, customize_pipeline=lambda env, pipeline: pipeline):
        pipeline_type = type(pipeline)
        if pipeline_type is str:
            value = env.getvar(pipeline)
            if type(value) is marcel.core.PipelineMarcel:
                return value
            else:
                raise marcel.exception.KillCommandException(
                    f'The variable {pipeline} is not bound to a pipeline: {pipeline_type}')
        elif pipeline_type is PipelineExecutable:
            return PipelineMarcel(pipeline, pipeline.source, customize_pipeline)
        elif pipeline_type is marcel.function.SourceFunction:
            # Callable, but indicates user error
            return None
        elif callable(pipeline) or pipeline_type is OpList:
            return PipelinePython(pipeline, customize_pipeline)
        else:
            return None

    @staticmethod
    def create_empty_pipeline(env):
        return (PipelinePython(marcel.core.OpList(env, None), None)
                if env.api_usage()
                else PipelineMarcel(marcel.core.PipelineExecutable(), '', None))

    # Internal

    def check_setup_state(self):
        assert self.state in (PipelineMarcel.State.IDLE, PipelineMarcel.State.SETUP), self.state


# A pipeline constructed through the marcel parser, via command line or script. Pipeline args are managed
# by the Environment's NestedNamspace, and are pushed/popped around pipeline execution.
class PipelineMarcel(Pipeline):
    
    # Pipeline execution is generally IDLE -> SETUP -> RUNNING. There are situations where pipeline use can encounter
    # two successive calls to setup(), so the transitions have to allow for that.
    class State(Enum):

        IDLE = auto()
        SETUP = auto()
        RUNNING = auto()
        
    def __init__(self, executable, source, customize_pipeline):
        super().__init__(executable, customize_pipeline)
        self.scope = None
        self.source = source
        self.state = PipelineMarcel.State.IDLE

    # Pipeline - execution

    def setup(self, env):
        assert self.state in (PipelineMarcel.State.IDLE, PipelineMarcel.State.SETUP), self.state
        if self.state is PipelineMarcel.State.IDLE:
            self.executable.setup(env)
            self.scope = {}
            if self.executable.params:
                for param in self.executable.params:
                    self.scope[param] = None
        self.state = PipelineMarcel.State.SETUP

    def run_pipeline(self, env, bindings):
        assert self.state in (PipelineMarcel.State.IDLE, PipelineMarcel.State.SETUP), self.state
        params = self.executable.parameters()
        assert set(params) == set(bindings.keys()), f'params = {params}, binding keys = {bindings.keys()}'
        env.vars().push_scope(bindings)
        try:
            with env.check_nesting():
                try:
                    # setup() might have been run already. If a pipeline is run by itself, then
                    # setup() hasn't been run and is needed here. But if a pipeline is receving
                    # input, then the containing pipeline's setup ensures that this pipeline's
                    # setup() has been run.
                    if self.state is PipelineMarcel.State.IDLE:
                        self.executable.setup(env)
                        self.state = PipelineMarcel.State.SETUP
                except marcel.exception.KillAndResumeException as e:
                    # KARE is fatal during setup.
                    raise marcel.exception.KillCommandException(str(e))
                try:
                    self.state = PipelineMarcel.State.RUNNING
                    self.executable.run(env)
                    self.executable.flush(env)
                finally:
                    self.executable.cleanup()
        finally:
            env.vars().pop_scope()
            self.state = PipelineMarcel.State.IDLE

    # Pipeline - construction

    def copy(self):
        return PipelineMarcel(self.executable.copy(), self.source, self.customize_pipeline)

    def append_immutable(self, op):
        return PipelineMarcel(self.executable.append_immutable(op), self.source, self.customize_pipeline)

    def route_output(self, receiver):
        self.executable.last_op().receiver = receiver

    # PipelineMarcel

    def run_in_main_process(self):
        return self.executable.first_op().run_in_main_process()


# A pipeline created by Python, by using marcel.api. Pipeline variables are ordinary Python variables,
# and scoping is taken care of by Python.
class PipelinePython(Pipeline):

    def __init__(self, pipeline, customize_pipeline):
        if callable(pipeline):
            executable = None
            self.pipeline_function = PipelineFunction(pipeline)
        elif type(pipeline) is OpList:
            executable = pipeline.create_executable_pipeline()
            self.pipeline_function = None
        elif type(pipeline) is PipelineExecutable:
            executable = pipeline
            self.pipeline_function = None
        else:
            assert False, pipeline
        super().__init__(executable, customize_pipeline)

    # Pipeline - execution

    def setup(self, env):
        pass

    def run_pipeline(self, env, bindings):
        if self.pipeline_function:
            params = self.executable.parameters()
            assert set(params) == set(bindings.keys()), f'params = {params}, binding keys = {bindings.keys()}'
            args = []
            for param in params:
                args.append(bindings[param])
            op_list = self.pipeline_function.create_pipeline(args)
            self.executable = op_list.create_executable_pipeline()
        try:
            self.executable.setup(env)
        except marcel.exception.KillAndResumeException as e:
            # KARE is fatal during setup.
            raise marcel.exception.KillCommandException(str(e))
        try:
            self.state = PipelineMarcel.State.RUNNING
            self.executable.run(env)
            self.executable.flush(env)
        finally:
            self.executable.cleanup()
            self.state = PipelineMarcel.State.IDLE

    # Pipeline - construction

    def append_immutable(self, op):
        return PipelinePython(self.executable.append_immutable(op), self.customize_pipeline)
