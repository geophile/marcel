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

class Renderable:

    def __repr__(self):
        """
        Return the __compact__.

        Args:
            self: (todo): write your description
        """
        return self.render_compact()

    def render_compact(self):
        """
        Returns a string representation.

        Args:
            self: (todo): write your description
        """
        return str(self)

    def render_full(self, color_scheme):
        """
        Render the full full full scheme.

        Args:
            self: (todo): write your description
            color_scheme: (todo): write your description
        """
        return str(self)
