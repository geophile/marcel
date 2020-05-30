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
import marcel.functionwrapper


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

    # BaseOp

    def setup_1(self):
        count = 0
        if self.string is not None:
            self.value = self.string
            count += 1
        if self.pipeline is not None:
            self.value = self.pipeline
            count += 1
        if self.function is not None:
            function = marcel.functionwrapper.FunctionWrapper(function=self.function)
            function.check_validity()
            function.set_op(self)
            self.value = function()
            count += 1
        assert count == 1

    def receive(self, _):
        self.env().setvar(self.var, self.value)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
