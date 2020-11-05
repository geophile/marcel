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

import marcel.op.apiop


def _first(output, unwrap_singleton, errors, error_handler):
    """
    Return the first error.

    Args:
        output: (todo): write your description
        unwrap_singleton: (str): write your description
        errors: (todo): write your description
        error_handler: (todo): write your description
    """
    return First(output, unwrap_singleton, errors, error_handler)


class First(marcel.op.apiop.APIOp):

    def __init__(self, output, unwrap_singleton, errors, error_handler):
        """
        Called when a singleton.

        Args:
            self: (todo): write your description
            output: (str): write your description
            unwrap_singleton: (todo): write your description
            errors: (str): write your description
            error_handler: (todo): write your description
        """
        super().__init__(output, unwrap_singleton, errors, error_handler, True)
