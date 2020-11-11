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
        self.args_arg = None
        self.args = None
        self.kwargs_arg = None
        self.kwargs = None
        self.pipeline = None

    def __repr__(self):
        return f'runpipeline({self.var} {self.args_arg})'

    # AbstractOp

    def setup(self):
        self.args = self.eval_function('args_arg')
        self.kwargs = self.eval_function('kwargs_arg')
        self.pipeline = self.getvar(self.var)
        if self.pipeline is None:
            raise marcel.exception.KillCommandException(
                f'The variable {self.var} is undefined.')
        if not isinstance(self.pipeline, marcel.core.Pipeline):
            raise marcel.exception.KillCommandException(
                f'The variable {self.var} is not bound to anything executable.')
        # Why copy: A pipeline can be used twice in a command, e.g.
        #    x = [a: ... ]
        #    x (1) | join [x (2)]
        # Without copying the identical ops comprising x would be used twice in the same
        # command. This potentially breaks the use of Op state during execution, and also
        # breaks the structure of the pipeline, e.g. Op.receiver.
        self.pipeline = self.pipeline.copy()
        self.pipeline.set_error_handler(self.owner.error_handler)
        self.pipeline.last_op().receiver = self.receiver

    def set_env(self, env):
        super().set_env(env)

    # Op

    def receive(self, x):
        self.env().vars().push_scope(self.pipeline_args())
        try:
            self.pipeline.setup()
            self.pipeline.set_env(self.env())
            self.pipeline.receive(x)
        finally:
            self.env().vars().pop_scope()

    def receive_complete(self):
        self.pipeline.receive_complete()
        self.send_complete()

    # RunPipeline

    def set_pipeline_args(self, args, kwargs):
        self.args_arg = args
        self.kwargs_arg = kwargs

    def pipeline_args(self):
        map = None
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
        return map