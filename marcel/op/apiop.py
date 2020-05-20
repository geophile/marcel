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


class APIOp(marcel.core.Op):

    def __init__(self, env, output, unwrap_singleton, errors, error_handler, stop_after_first):
        super().__init__(env)
        self.unwrap_singleton = unwrap_singleton
        self.stop_after_first = stop_after_first
        self.output = output
        self.errors = errors
        self.error_handler = (self.error_to_output if errors is None and error_handler is None else
                              self.error_to_errors if errors is not None and error_handler is None else
                              error_handler if errors is None and error_handler is not None else
                              None)  # indicates incorrect use of errors and error_handler args

    def __repr__(self):
        return f'{self.op_name()}()'

    # BaseOp

    def setup_1(self):
        self.check_arg(self.error_handler is not None,
                       None,
                       'Specify at most one of the errors and error_handler arguments.')

    def receive(self, x):
        if self.unwrap_singleton and len(x) == 1:
            x = x[0]
        self.output.append(x)
        if self.stop_after_first:
            marcel.exception.StopAfterFirst()

    def receive_error(self, error):
        self.error_handler(self.env(), error)
        if self.stop_after_first:
            marcel.exception.StopAfterFirst()

    # For use by this class

    def error_to_output(self, env, error):
        self.output.append(error)

    def error_to_errors(self, env, error):
        self.errors.append(error)
