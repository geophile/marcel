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

import pathlib

import marcel.exception


class Locations(object):

    def __init__(self, env):
        self.env = env
        self.home = pathlib.Path.home().expanduser()

    def config_path(self):
        return self._dir('XDG_CONFIG_HOME', '.config') / 'startup.py'

    def history_path(self):
        return self._dir('XDG_DATA_HOME', '.local', 'share') / 'history'

    def _dir(self, xdg_var, *path_from_base):
        base = self.env.getvar(xdg_var)
        if base is None:
            base = self.home
            for dir in path_from_base:
                base = base / dir
        else:
            if type(base) is not str:
                raise marcel.exception.KillShellException(
                    f'Type of {xdg_var} is {type(base)}. If defined, it must be a string.')
            base = pathlib.Path(base).expanduser()
        dir = base / 'marcel'
        if dir.exists():
            if not dir.is_dir():
                raise marcel.exception.KillShellException(f'Not a directory: {dir}')
        else:
            dir.mkdir(exist_ok=False)
        return dir

