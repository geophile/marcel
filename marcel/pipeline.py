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

import marcel.core
import marcel.env
import marcel.exception
import marcel.function
import marcel.helpformatter
import marcel.object.error
import marcel.opmodule
import marcel.util

# CLI ------------------------------------------------------------------------------------------------------------------

# A PipelineExecutable is created via the CLI, and is also executable. All
class PipelineExecutable(object):

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

    # PipelineExecutable - execution

    def setup(self, env):
        prev_op = None
        for op in self.ops:
            if isinstance(op, marcel.core.Op) and op is not self.ops[0] and op.must_be_first_in_pipeline():
                raise marcel.exception.KillCommandException(
                    f'{op.op_name()} cannot receive input from a pipe')
            if prev_op:
                prev_op.receiver = op
            prev_op = op
        for op in self.ops:
            if env.trace.is_enabled():
                env.trace.write(op, 'SETUP')
            op.setup(env)
        for op in self.ops:
            op.customize_pipelines(env)

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

    # PipelineExecutable - construction

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

    def ensure_functions_compiled(self, globals):
        for op in self.ops:
            op.ensure_functions_compiled(globals)

    # PipelineExecutable

    def first_op(self):
        return self.ops[0]

    def last_op(self):
        return self.ops[-1]

    def n_params(self):
        return len(self.params)


# API ------------------------------------------------------------------------------------------------------------------

# The API constructs a pipelines by or-ing together ops.
# This class is written to work as both the object returned for each op, and the accumulator. E.g.
# map() | select() | red()
# 1. map() returns an OpList with op = map()
# 2. select() returns an OpList with op = select()
# 3. These OpLists are or-ed, returning an OpList placing map() and select() into ops.
# 4. Then red() yields an OpList with op set to red(), and that is or-ed appending to OpList.ops from step 3.
class OpList(object):

    def __init__(self, env, op):
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
        return PipelineIterator(self.env, PipelineOpList(self))

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


# Pipeline--------------------------------------------------------------------------------------------------------------

# There are a few kinds of pipelines:
# - PipelineExecutable: Created directly by Parser, and used for execution of pipelines.
# - OpList: Constructed by marcel.api, can be used to generate PipelineExecutable.
# - function evaluated to OpList: Also constructed by marcel.api, for parameterized pipelines.
# - PipelineFunction: Wrapper around function that evaluates to OpList.
# Pipeline provides a uniform interface to all of these. There are subclasses (PipelineMarcel, PipelinePython)
# corresponding to script/interactive vs. API usage. E.g. PipelineMarcel pipelines need parameters and scopes
# explicitly managed while PipelinePython pipelines do not.
class Pipeline(object):

    def __init__(self, executable):
        # executable is None if we're using the API, and the pipeline is specified as a lambda.
        assert executable is None or isinstance(executable, PipelineExecutable), type(executable)
        self.executable = executable

    def __repr__(self):
        return f'{self.__class__.__name__}({self.executable})'

    # Pipeline - execution

    def setup(self, env):
        assert False, self

    def receive(self, env, x):
        self.executable.receive(env, x)

    def flush(self, env):
        self.executable.flush(env)

    def cleanup(self):
        self.executable.cleanup()

    def parameters(self):
        return self.executable.parameters()

    def run_pipeline(self, env, bindings):
        assert False, self

    # Pipeline - construction

    def copy(self):
        assert False, self

    def append(self, op):
        self.executable.append(op)

    def append_immutable(self, op):
        self.executable.append_immutable(op)

    def route_output(self, receiver):
        assert False, self

    def ensure_terminal_write(self, env):
        if not self.executable.last_op().op_name() == 'write':
            self.executable = self.executable.append_immutable(marcel.opmodule.create_op(env, 'write'))

    def ensure_functions_compiled(self, env):
        self.executable.ensure_functions_compiled(env)

    # Pipeline - transmission

    def pickle(self, env, pickler):
        pickler.dump(self.executable)

    @staticmethod
    def create(env, pipeline):
        pipeline_type = type(pipeline)
        if pipeline_type is str:
            value = env.getvar(pipeline)
            if type(value) is PipelineMarcel:
                return value
            else:
                raise marcel.exception.KillCommandException(
                    f'The variable {pipeline} is not bound to a pipeline: {pipeline_type}')
        elif pipeline_type is PipelineExecutable:
            # Construction from a PE should only happen in the CLI, after parsing the command line.
            return PipelineMarcel(pipeline, pipeline.source)
        elif pipeline_type is marcel.function.SourceFunction:
            # Callable, but indicates user error
            return None
        elif pipeline_type is OpList:
            return PipelineOpList(pipeline)
        elif callable(pipeline) or pipeline_type is OpList:
            return PipelineFunction(pipeline)
        else:
            return None

    @staticmethod
    def create_empty_pipeline(env):
        return (PipelineOpList(OpList(env, None))
                if env.api_usage()
                else PipelineMarcel(PipelineExecutable(), ''))


# A pipeline constructed through the marcel parser, via command line or script. Pipeline args are managed
# by the Environment's NestedNamspace, and are pushed/popped around pipeline execution.
class PipelineMarcel(Pipeline):
    # Pipeline execution is generally IDLE -> SETUP -> RUNNING. There are situations where pipeline use can encounter
    # two successive calls to setup(), so the transitions have to allow for that.
    class State(Enum):

        IDLE = auto()
        SETUP = auto()
        RUNNING = auto()

    def __init__(self, executable, source):
        super().__init__(executable)
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
        return PipelineMarcel(self.executable.copy(), self.source)

    def append_immutable(self, op):
        return PipelineMarcel(self.executable.append_immutable(op), self.source)

    def route_output(self, receiver):
        self.executable.last_op().receiver = receiver

    # PipelineMarcel

    def run_in_main_process(self):
        return self.executable.first_op().run_in_main_process()


# A pipeline created throught the API, running code invoking ops, e.g. gen(3) | map(lambda: ...).
# Such pipelines never have args
class PipelineOpList(Pipeline):

    def __init__(self, pipeline):
        # PE needed to support append_immutable
        if type(pipeline) is OpList:
            super().__init__(pipeline.create_executable_pipeline())
        elif type(pipeline) is PipelineExecutable:
            super().__init__(pipeline)
        else:
            assert False, type(pipeline)

    # Pipeline - execution

    def setup(self, env):
        pass

    def run_pipeline(self, env, bindings):
        try:
            self.executable.setup(env)
        except marcel.exception.KillAndResumeException as e:
            # KARE is fatal during setup.
            raise marcel.exception.KillCommandException(str(e))
        try:
            self.executable.run(env)
            self.executable.flush(env)
        finally:
            self.executable.cleanup()

    # Pipeline - construction

    def copy(self):
        return PipelineOpList(self.executable)

    def append_immutable(self, op):
        return PipelineOpList(self.executable.append_immutable(op))

    def route_output(self, receiver):
        self.executable.last_op().receiver = receiver


# Used to represent a function yielding an OpList (which then yields a Pipeline).
class PipelineFunction(Pipeline):

    class Customizations(object):

        # For a PipelineFunction, the executable form of the pipeline only exists at runtime.
        # Customizations have to be saved up until then.
        def __init__(self):
            self.ops = []
            self.receiver = None

        def __repr__(self):
            buffer = [str(op) for op in self.ops]
            if self.receiver:
                buffer.append(self.receiver)
            return f'({", ".join(buffer)})'

    def __init__(self, function):
        assert callable(function), type(function)
        super().__init__(None)
        self.function = function
        self.customizations = PipelineFunction.Customizations()

    def __repr__(self):
        return f'PipelineFunction({self.function} {self.customizations})'

    # Pipeline - execution

    def setup(self, env):
        pass

    def parameters(self):
        return self.function.__code__.co_varnames

    def run_pipeline(self, env, bindings):
        self.create_executable(env, bindings)
        import os
        try:
            self.executable.setup(env)
        except marcel.exception.KillAndResumeException as e:
            # KARE is fatal during setup.
            raise marcel.exception.KillCommandException(str(e))
        try:
            self.executable.run(env)
            self.executable.flush(env)
        finally:
            self.executable.cleanup()

    # Pipeline - construction

    def copy(self):
        return PipelineFunction(self.function)

    def append(self, op):
        self.customizations.ops.append(op)

    def append_immutable(self, op):
        self.customizations.ops.append(op)
        return self

    def route_output(self, receiver):
        self.customizations.receiver = receiver

    # Pipeline - transmission

    def pickle(self, env, pickler):
        self.ensure_executable(env)
        pickler.dump(self.executable)

    # PipelineFunction internal

    def ensure_executable(self, env):
        if self.executable is None:
            self.create_executable(env, )

    def create_executable(self, env, bindings):
        # Create args to the pipeline-creating function
        params = self.parameters()
        assert set(params) == set(bindings.keys()), f'params = {params}, binding keys = {bindings.keys()}'
        args = []
        for param in params:
            args.append(bindings[param])
        # Create the OpList
        op_list = self.function(*args)
        # Append customization ops
        for op in self.customizations.ops:
            new_op = OpList(env, op)
            op_list = (op_list | new_op) if op_list else new_op
        self.executable = op_list.create_executable_pipeline()
        if self.customizations.receiver:
            self.executable.last_op().receiver = self.customizations.receiver


class PipelineIterator:

    def __init__(self, env, pipeline):
        assert isinstance(pipeline, Pipeline), type(pipeline)
        output = []
        gather_op = env.op_modules['gather'].api_function()(output)
        pipeline.append(gather_op)
        try:
            pipeline.run_pipeline(env, {})
        except marcel.exception.KillCommandException as e:
            marcel.util.print_to_stderr(env, e)
        finally:
            self.iterator = iter(output)

    def __next__(self):
        return next(self.iterator)



def convert_to_pipeline(env, x):
    if isinstance(x, str):
        x = marcel.util.string_value(x)
    return x if isinstance(x, Pipeline) else Pipeline.create(env, x)
