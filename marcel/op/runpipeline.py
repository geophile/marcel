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

import marcel.core
import marcel.exception
import marcel.util


class RunPipeline(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.var = None
        self.args_arg = None
        self.args = None
        self.kwargs_arg = None
        self.kwargs = None
        self.pipeline = None

    def __repr__(self):
        return f'runpipeline({self.var} {self.args_arg})'

    # AbstractOp

    def setup(self, env):
        self.args = self.eval_function(env, 'args_arg')
        self.kwargs = self.eval_function(env, 'kwargs_arg')
        self.pipeline = env.getvar(self.var)
        if self.pipeline is None:
            raise marcel.exception.KillCommandException(
                f'{self.var} is not executable.')
        if not isinstance(self.pipeline, marcel.core.PipelineExecutable):
            raise marcel.exception.KillCommandException(
                f'The variable {self.var} is not bound to anything executable.')
        n_params = 0 if self.pipeline.parameters() is None else len(self.pipeline.parameters())
        n_args = 0 if self.args is None else len(self.args)
        n_kwargs = 0 if self.kwargs is None else len(self.kwargs)
        if n_params < n_args + n_kwargs:
            raise marcel.exception.KillCommandException(
                f'Too many arguments for pipeline {self.var} = {self.pipeline}')
        # Why copy: A pipelines can be used twice in a command, e.g.
        #    f = (| a: ... |)
        #    f (1) | join (| f (2) |)
        # Without copying the identical ops comprising f would be used twice in the same
        # command. This potentially breaks the use of Op state during execution, and also
        # breaks the structure of the pipelines, e.g. Op.receiver.
        self.pipeline = self.pipeline.copy()
        self.pipeline.last_op().receiver = self.receiver
        env.vars().push_scope(self.pipeline_args())
        try:
            self.pipeline.setup(env)
        finally:
            env.vars().pop_scope()

    # Op

    def run(self, env):
        env.vars().push_scope(self.pipeline_args())
        try:
            self.pipeline.run(env)
        finally:
            env.vars().pop_scope()

    def receive(self, env, x):
        env.vars().push_scope(self.pipeline_args())
        try:
            self.pipeline.receive(env, x)
        finally:
            env.vars().pop_scope()

    def flush(self, env):
        env.vars().push_scope(self.pipeline_args())
        try:
            self.pipeline.flush(env)
            self.propagate_flush(env)
        finally:
            env.vars().pop_scope()

    def cleanup(self):
        self.pipeline.cleanup()

    # RunPipeline

    def set_pipeline_args(self, args, kwargs):
        self.args_arg = args
        self.kwargs_arg = kwargs

    def pipeline_args(self):
        pipeline_arg_bindings = None
        params = self.pipeline.parameters()
        if params is not None:
            pipeline_arg_bindings = {}
            # Set anonymous args
            if self.args is not None:
                if len(self.args) > len(params):
                    raise marcel.exception.KillCommandException(
                        f'Provided {len(self.args)} arguments for {len(params)} pipeline parameter(s)')
                for i in range(len(self.args)):
                    pipeline_arg_bindings[params[i]] = self.args[i]
            # Set named args
            if self.kwargs is not None:
                already_set = set(pipeline_arg_bindings.keys()).intersection(self.kwargs.keys())
                if len(already_set) > 0:
                    raise marcel.exception.KillCommandException(
                        f'Attempt to set these arguments twice (anonymous and named): {", ".join(already_set)}')
                pipeline_arg_bindings.update(self.kwargs)
            all_params = set(params)
            unset = all_params.difference(pipeline_arg_bindings.keys())
            for param in unset:
                pipeline_arg_bindings[param] = None
        return pipeline_arg_bindings
