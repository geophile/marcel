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

import os
import tempfile

import marcel.picklefile


RESERVOIRS = set()


def shutdown(main_pid):
    if os.getpid() == main_pid:
        for reservoir in RESERVOIRS:
            reservoir.close()
            reservoir.ensure_deleted()
        RESERVOIRS.clear()


# A Reservoir collects and feeds streams.

class Reservoir(marcel.picklefile.PickleFile):

    FLUSH_INTERVAL_SEC = 1

    def __init__(self, name, path=None):
        super().__init__(tempfile.mkstemp()[1] if path is None else path)
        self.name = name
        RESERVOIRS.add(self)
