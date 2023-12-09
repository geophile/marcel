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
import pathlib

import marcel.exception


class Locations(object):

    def __init__(self):
        self.home = None
        self.config_base = None
        self.data_base = None
        self.setup(None, None, None)

    # Exposed for workspace testing
    def setup(self, home, config_base, data_base):
        self.home = Locations.normalize_dir(
            'home directory',
            home,
            pathlib.Path.home())
        self.config_base = Locations.normalize_dir(
            'application configuration directory (e.g. XDG_CONFIG_HOME)',
            config_base,
            os.getenv('XDG_CONFIG_HOME'),
            self.home / '.config')
        self.data_base = Locations.normalize_dir(
            'application data directory (e.g. XDG_DATA_HOME)',
            data_base,
            os.getenv('XDG_DATA_HOME'),
            self.home / '.local' / 'share')

    def config_dir_path(self, ws_name):
        path = Locations.marcel_dir(self.config_base)
        if ws_name is not None:
            path = path / ws_name
        return path

    def data_dir_path(self, ws_name):
        path = Locations.marcel_dir(self.data_base)
        if ws_name is not None:
            path = path / ws_name
        return path

    def config_file_path(self, ws_name):
        return self.config_dir_path(ws_name) / 'startup.py'

    def history_file_path(self, ws_name):
        return self.data_dir_path(ws_name) / 'history'

    def workspace_properties_file_path(self, ws_name):
        return self.data_dir_path(ws_name) / 'properties.pickle'

    def workspace_environment_file_path(self, ws_name):
        return self.data_dir_path(ws_name) / 'env.pickle'

    def workspace_marker_file_path(self, ws_name):
        return self.config_dir_path(ws_name) / '.WORKSPACE'

    @staticmethod
    def marcel_dir(base):
        dir = base / 'marcel'
        if dir.exists():
            if not dir.is_dir():
                raise marcel.exception.KillShellException(f'Not a directory: {dir}')
        else:
            dir.mkdir(exist_ok=False, parents=True)
        return dir

    @staticmethod
    def normalize_dir(description, provided, *defaults):
        dir = provided
        d = 0
        while dir is None and d < len(defaults):
            dir = defaults[d]
            d += 1
        if dir is None:
            raise marcel.exception.KillShellException(
                f'Unable to start because value of {description} cannot be determined.')
        try:
            if not isinstance(dir, pathlib.Path):
                dir = pathlib.Path(dir)
            dir = dir.expanduser()
        except Exception as e:
            raise marcel.exception.KillShellException(
                f'Unable to start because value of {description} cannot be determined: {e}')
        return dir
