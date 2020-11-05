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

import marcel.object.renderable
import marcel.util


class Error(marcel.object.renderable.Renderable):

    def __init__(self, cause):
        """
        Initialize the label.

        Args:
            self: (todo): write your description
            cause: (todo): write your description
        """
        assert type(cause) is not Error
        self.message = str(cause)
        self.label = None  # Thread label, for forked execution

    def __repr__(self):
        """
        Return the __compact__.

        Args:
            self: (todo): write your description
        """
        return self.render_compact()

    # Renderable

    def render_compact(self):
        """
        Render the label.

        Args:
            self: (todo): write your description
        """
        return (f'Error: {self.message}'
                if self.label is None else
                f'Error({self.label}): {self.message}')

    def render_full(self, color_scheme):
        """
        Render the given color_scheme.

        Args:
            self: (todo): write your description
            color_scheme: (todo): write your description
        """
        out = self.render_compact()
        if color_scheme:
            out = marcel.util.colorize(out, color_scheme.error)
        return out

    # Error

    def set_label(self, label):
        """
        Set the label of a label.

        Args:
            self: (todo): write your description
            label: (str): write your description
        """
        self.label = label
