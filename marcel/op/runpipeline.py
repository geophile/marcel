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
import marcel.pipeline
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
        def ifnone(x, default):
            return default if x is None else x
        self.args = ifnone(self.eval_function(env, 'args_arg'), [])
        self.kwargs = ifnone(self.eval_function(env, 'kwargs_arg'), {})
        self.pipeline = env.getvar(self.var)
        if self.pipeline is None:
            raise marcel.exception.KillCommandException(
                f'The value of {self.var} is None, so it is not executable.')
        if not isinstance(self.pipeline, marcel.pipeline.PipelineMarcel):
            raise marcel.exception.KillCommandException(
                f'The variable {self.var} is not bound to anything executable.')
        n_params = len(self.pipeline.parameters())
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
        self.pipeline.route_output(self.receiver)
        env.vars().push_scope(self.bindings())
        try:
            self.pipeline.setup(env)
        finally:
            env.vars().pop_scope()

    # Op

    def run(self, env):
        bindings = self.bindings()
        env.vars().push_scope(bindings)
        try:
            self.pipeline.run_pipeline(env, bindings)
        finally:
            env.vars().pop_scope()

    def receive(self, env, x):
        env.vars().push_scope(self.bindings())
        try:
            self.pipeline.receive(env, x)
        finally:
            env.vars().pop_scope()

    def flush(self, env):
        env.vars().push_scope(self.bindings())
        try:
            self.pipeline.flush(env)
            self.propagate_flush(env)
        finally:
            env.vars().pop_scope()

    def cleanup(self):
        if self.pipeline:
            self.pipeline.cleanup()

    # RunPipeline

    def set_pipeline_args(self, args, kwargs):
        assert type(args) is list, args
        assert type(kwargs) is dict, kwargs
        self.args_arg = args
        self.kwargs_arg = kwargs

    def bindings(self):
        params = self.pipeline.parameters()
        bindings = {}
        # Set anonymous args
        if len(self.args) > len(params):
            raise marcel.exception.KillCommandException(
                f'Provided {len(self.args)} arguments for {len(params)} pipeline parameter(s)')
        for i in range(len(self.args)):
            bindings[params[i]] = self.args[i]
        # Set named args
        if self.kwargs is not None:
            already_set = set(bindings.keys()).intersection(self.kwargs.keys())
            if len(already_set) > 0:
                raise marcel.exception.KillCommandException(
                    f'Attempt to set these arguments twice (anonymous and named): {", ".join(already_set)}')
            bindings.update(self.kwargs)
        all_params = set(params)
        unset = all_params.difference(bindings.keys())
        for param in unset:
            bindings[param] = None
        return bindings
