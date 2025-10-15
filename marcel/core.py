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

    def ensure_functions_compiled(self, globals):
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
            self.fatal_error(env, args_description, f'{type(e)}: {e}')

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

    def ensure_function_compiled(self, arg, globals):
        if type(arg) is marcel.function.SourceFunction:
            arg.ensure_compiled(globals)


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

    def ensure_functions_compiled(self, globals):
        self.pipeline.ensure_functions_compiled(globals)