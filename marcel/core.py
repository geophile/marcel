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


class AbstractOp(Pipelineable):

    def __repr__(self):
        assert False

    # AbstractOp

    def setup_1(self):
        pass

    def setup_2(self):
        pass


class ShallowCopyStore:

    def __init__(self):
        self.contents = {}
        self.counter = 0

    def save(self, x):
        id = self.counter
        self.counter += 1
        self.contents[id] = x
        return id

    def recall(self, id):
        return self.contents.pop(id, None)


class Op(AbstractOp):

    # Op sublcasses use Op.save and Op.recall to "hide" state that should not be deep-copied during
    # pickling/unpickling. For example, the variables passed to the store/load ops, via the API, are
    # bound to lists. If these lists were copied, then pipeline copies would operate on the copied lists,
    # defeating the point of using the store/load ops to operate on the values bound to the variables.
    shallow_copy_store = ShallowCopyStore()

    def __init__(self, env):
        super().__init__()
        self._env = env
        # The next op in the pipeline, or None if this is the last op in the pipeline.
        self.next_op = None
        # receiver is where op output is sent. Same as next_op unless this is the last
        # op in the pipeline. In which case, the receiver is that of the pipeline containing
        # this one.
        self.receiver = None
        # The pipeline to which this op belongs
        self.owner = None

    def __repr__(self):
        assert False, self.op_name()

    def __iter__(self):
        return PipelineIterator(self.create_pipeline())

    def __getstate__(self):
        m = self.__dict__.copy()
        m['_env_ref'] = self.save(self._env)
        return m

    def __setstate__(self, state):
        env_ref = self.recall(state['_env_ref'])
        if env_ref is not None:
            # Local copy: Use the saved env
            state['_env'] = env_ref
        # else: Remote copy: Keep the transmitted env
        self.__dict__.update(state)

    # Pipelineable

    def create_pipeline(self):
        pipeline = Pipeline()
        pipeline.append(self.copy())
        return pipeline

    # Op

    def set_owner(self, pipeline):
        self.owner = pipeline

    def connect(self, new_op):
        self.next_op = new_op

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
        assert self._env is not None, self
        return self._env

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

    @staticmethod
    def save(x):
        return Op.shallow_copy_store.save(x)

    @staticmethod
    def recall(id):
        return Op.shallow_copy_store.recall(id)

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

    def getvar(self, var):
        value = self.owner.args.get(var, None) if self.owner.args else None
        if value is None:
            value = self.env().getvar(var)
        return value

    # arg is a Pipeline, Pipelineable, or a var bound to a pipeline. Deal with all of these possibilities
    # and come up with the pipeline itself.
    def pipeline_arg(self, arg):
        if type(arg) is marcel.core.Pipeline:
            pipeline = arg
        elif isinstance(arg, marcel.core.Pipelineable):
            pipeline = arg.create_pipeline()
        elif type(arg) is str:  # Presumably a var
            pipeline = self.env().getvar(arg)
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
        state = self.__dict__
        val = state[field]
        if callable(val):
            val = val()
            if len(types) > 0 and type(val) not in types:
                raise marcel.exception.KillCommandException(
                    f'Type of {self.op_name()}.{field} is {type(val)}, but must be one of {types}')
            state[field] = val
        elif type(val) in (tuple, list):
            evaled = []
            for x in val:
                if callable(x):
                    x = x()
                    if len(types) > 0 and type(x) not in types:
                        raise marcel.exception.KillCommandException(
                            f'Type of {self.op_name()}.{field} element {x} is {type(x)}, but must be one of {types}')
                evaled.append(x)
            state[field] = evaled
        elif type(val) is dict:
            evaled = {}
            for k, v in val.items():
                if callable(v):
                    v = v()
                    if len(types) > 0 and type(v) not in types:
                        raise marcel.exception.KillCommandException(
                            f'Type of {self.op_name()}.{field} element {v} is {type(v)}, but must be one of {types}')
                evaled[k] = v
            state[field] = evaled

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
        AbstractOp.__init__(self)
        self.error_handler = None
        self.first_op = None
        self.last_op = None
        # Parameters declared for a pipeline
        self.params = None
        # dict containing actual values, combining positional args (getting the name from params)
        # and kwargs.
        self.args = None

    def __repr__(self):
        params = ', '.join(self.params) if self.params else None
        op_buffer = []
        op = self.first_op
        while op:
            op_buffer.append(str(op))
            op = op.next_op
        ops = ' | '.join(op_buffer)
        return f'[{params}: {ops}]' if params else f'[{ops}]'

    def env(self):
        return self.first_op.env()

    def set_error_handler(self, error_handler):
        self.error_handler = error_handler

    def handle_error(self, error):
        self.error_handler(self.env(), error)

    # Pipelineable

    def create_pipeline(self):
        return self

    # AbstractOp

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

    def set_parameters(self, parameters):
        if parameters is not None:
            assert len(parameters) > 0
            self.params = parameters

    def parameters(self):
        return self.params

    def set_parameter_values(self, args, kwargs):
        self.args = {}
        if args:
            for i in range(len(args)):
                self.args[self.params[i]] = args[i]
        if kwargs:
            self.args.update(kwargs)

    def clear_parameter_values(self):
        self.args = None

    def copy(self):
        return marcel.util.copy(self)

    def append(self, op):
        op.set_owner(self)
        if self.last_op:
            assert self.first_op is not None
            self.last_op.connect(op)
        else:
            assert self.first_op is None
            self.first_op = op
        self.last_op = op

    def prepend(self, op):
        op.set_owner(self)
        if self.first_op:
            assert self.last_op is not None
            op.connect(self.first_op)
        else:
            assert self.last_op is None
            self.last_op = op
        self.first_op = op

    def is_terminal_op(self, op_name):
        return self.last_op.op_name() == op_name


class Command:

    def __init__(self, source, pipeline):
        self.source = source
        self.pipeline = pipeline

    def __repr__(self):
        return str(self.pipeline)

    def execute(self):
        env = self.pipeline.env()
        env.clear_changes()
        self.pipeline.setup_1()
        self.pipeline.setup_2()
        self.pipeline.receive(None)
        self.pipeline.receive_complete()
        # A Command is executed by a multiprocessing.Process. Need to transmit the Environment's vars
        # relating to the directory, to the parent process, because they may have changed.
        return env.changes()


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


class LoopVar:

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.empty = True

    def __iter__(self):
        return self

    def __next__(self):
        if self.empty:
            raise StopIteration()
        self.empty = True
        return ()

    def append(self, value):
        self.pipeline.set_parameter_values(value, None)
        self.empty = False
