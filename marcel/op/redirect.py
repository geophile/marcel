# This file is part of Marcel.
#
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
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


# Op for redirecting output from an op's pipeline to the parent pipeline's output.
class Redirect(marcel.core.Op):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def __repr__(self):
        return 'redirect()'

    def receive(self, env, x):
        self.parent.send(env, x)

    def receive_error(self, env, error):
        self.parent.send_error(env, error)
