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
        # self.args is a list of flags (short or long) and values. Can't be handled via ArgsParser
        # because we don't know what the flags are, they are just the unbound variables in the pipeline's
        # functions.
        self.args = None
        self.pipeline = None
        self.locals = None

    def __repr__(self):
        return f'runpipeline({self.var})'

    # AbstractOp

    def setup_1(self):
        assert self.pipeline is None
        self.eval_function('args')
        self.create_local_namespace()
        pipeline = self.env().getvar(self.var)
        if pipeline is None:
            raise marcel.exception.KillCommandException(
                f'The variable {self.var} is undefined.')
        if not isinstance(pipeline, marcel.core.Pipeline):
            raise marcel.exception.KillCommandException(
                f'The variable {self.var} is not bound to anything executable.')
        self.pipeline = pipeline.copy()
        self.pipeline.set_error_handler(self.owner.error_handler)
        self.pipeline.setup_1()
        self.pipeline.last_op.receiver = self.receiver

    def receive(self, x):
        namespace = self.pipeline.first_op.env().namespace
        namespace.update(self.locals)
        self.pipeline.receive(x)
        for var in self.locals:
            del namespace[var]

    def receive_complete(self):
        self.pipeline.receive_complete()

    # RunPipeline

    def create_local_namespace(self):
        self.locals = {}
        key = None
        for arg in self.args:
            if key is None:
                # Expect a flag, either short or long syntax.
                if arg.startswith('---'):
                    raise marcel.exception.KillCommandException(f'Invalid argument: {arg}')
                elif arg.startswith('--'):
                    key = arg[2:]
                elif arg.startswith('-'):
                    key = arg[1:]
                else:
                    raise marcel.exception.KillCommandException(f'Invalid argument: {arg}')
                if not key.isidentifier():
                    raise marcel.exception.KillCommandException(f'Expected flag, found {arg}')
            else:
                self.locals[key] = arg
                key = None
