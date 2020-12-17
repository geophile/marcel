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
import marcel.function


class Assign(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.string = None
        self.pipeline = None
        self.function = None
        self.value = None

    def __repr__(self):
        return f'assign({self.var}, {self.value})'

    # AbstractOp

    def setup(self):
        assert self.var is not None
        count = 0
        if self.string is not None:
            assert type(self.string) is str, type(self.string)
            self.value = self.string
            count += 1
        if self.pipeline is not None:
            assert type(self.pipeline) is marcel.core.Pipeline, type(self.pipeline)
            self.value = self.pipeline
            count += 1
        if self.function is not None:
            assert isinstance(self.function, marcel.function.Function), type(self.function)
            self.value = self.call(self.function)
            count += 1
        assert count == 1, count

    def set_env(self, env):
        super().set_env(env)
        if isinstance(self.value, marcel.function.Function):
            self.value.set_globals(env.vars())

    def run(self):
        self.env().setvar(self.var, self.value)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
