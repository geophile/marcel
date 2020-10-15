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

import marcel.core
import marcel.exception


class RunPipeline(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.args = None
        self.kwargs = None
        self.pipeline = None

    def __repr__(self):
        return f'runpipeline({self.pipeline})'

    # AbstractOp

    def setup(self):
        self.args = self.eval_function('args')
        self.kwargs = self.eval_function('kwargs')
        pipeline = self.getvar(self.var)
        if pipeline is None:
            raise marcel.exception.KillCommandException(
                f'The variable {self.var} is undefined.')
        if not isinstance(pipeline, marcel.core.Pipeline):
            raise marcel.exception.KillCommandException(
                f'The variable {self.var} is not bound to anything executable.')
        self.pipeline = pipeline.copy()
        self.pipeline.set_error_handler(self.owner.error_handler)
        self.pipeline.last_op().receiver = self.receiver
        self.pipeline.setup()
        self.set_args()

    def set_env(self, env):
        super().set_env(env)
        self.pipeline.set_env(env)

    # Op

    def receive(self, x):
        self.pipeline.receive(x)

    def receive_complete(self):
        self.pipeline.receive_complete()
        if self.pipeline.parameters() is not None:
            self.env().namespace.pop_scope()
        self.send_complete()

    # RunPipeline

    def set_pipeline_args(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

    def set_args(self):
        params = self.pipeline.parameters()
        if params is not None:
            map = {}
            # Set anonymous args
            if self.args is not None:
                if len(self.args) > len(params):
                    raise marcel.exception.KillCommandException(
                        f'Provided {len(self.args)} arguments, but there are only {len(params)} pipeline parameters')
                for i in range(len(self.args)):
                    map[params[i]] = self.args[i]
            # Set named args
            if self.kwargs is not None:
                already_set = set(map.keys()).intersection(self.kwargs.keys())
                if len(already_set) > 0:
                    raise marcel.exception.KillCommandException(
                        f'Attempt to set these arguments twice (anonymous and named): {already_set}')
                map.update(self.kwargs)
            if len(map) != len(params):
                raise marcel.exception.KillCommandException(f'Expected arguments: {len(params)}, given: {len(map)}')
            self.env().namespace.push_scope(map)
