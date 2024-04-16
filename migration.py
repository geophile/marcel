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

import version
from locations import Locations


class Migration(object):

    @staticmethod
    def current_version():
        return version.VERSION[:version.VERSION.rfind('.')]

    PREHISTORIC = '0.0'  # Anything before 0.24
    POINTS = [PREHISTORIC, current_version()]

    def __init__(self):
        self.locations = Locations()

    def go_forward(self):
        assert False

    def go_backward(self):
        assert False

    @staticmethod
    def go_forward_to_current():
        pass

    def go_backward_to_version(self, version):
        pass
