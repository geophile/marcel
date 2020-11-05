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

    def __init__(self, output, unwrap_singleton, errors, error_handler, stop_after_first):
        """
        Initialize the singleton.

        Args:
            self: (todo): write your description
            output: (str): write your description
            unwrap_singleton: (todo): write your description
            errors: (str): write your description
            error_handler: (todo): write your description
            stop_after_first: (str): write your description
        """
        super().__init__(None)
        self.unwrap_singleton = unwrap_singleton
        self.stop_after_first = stop_after_first
        self.output = output
        self.errors = errors
        self.error_handler = (self.error_to_output if errors is None and error_handler is None else
                              self.error_to_errors if errors is not None and error_handler is None else
                              error_handler if errors is None and error_handler is not None else
                              None)  # indicates incorrect use of errors and error_handler args

    def __repr__(self):
        """
        Return a repr representation of a repr__.

        Args:
            self: (todo): write your description
        """
        return f'{self.op_name()}()'

    # AbstractOp

    def setup(self):
        """
        Setup the error handler.

        Args:
            self: (todo): write your description
        """
        self.check_arg(self.error_handler is not None,
                       None,
                       'Specify at most one of the errors and error_handler arguments.')

    def receive(self, x):
        """
        Receive a single chunk.

        Args:
            self: (todo): write your description
            x: (todo): write your description
        """
        if self.unwrap_singleton and len(x) == 1:
            x = x[0]
        self.output.append(x)
        if self.stop_after_first:
            marcel.exception.StopAfterFirst()

    def receive_error(self, error):
        """
        Called when an error.

        Args:
            self: (todo): write your description
            error: (todo): write your description
        """
        self.error_handler(self.env(), error)
        if self.stop_after_first:
            marcel.exception.StopAfterFirst()

    # For use by this class

    def error_to_output(self, env, error):
        """
        Outputs an error.

        Args:
            self: (todo): write your description
            env: (todo): write your description
            error: (todo): write your description
        """
        self.output.append(error)

    def error_to_errors(self, env, error):
        """
        Add an error message to the list.

        Args:
            self: (todo): write your description
            env: (todo): write your description
            error: (todo): write your description
        """
        self.errors.append(error)
