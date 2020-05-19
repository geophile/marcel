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


def _gather(env, output, unwrap_singleton=True, errors=None, error_handler=None):
    return Gather(env, output, unwrap_singleton, errors, error_handler)


class Gather(marcel.op.apiop.APIOp):

    def __init__(self, env, output, unwrap_singleton, errors, error_handler):
        super().__init__(env, output, unwrap_singleton, errors, error_handler, False)
