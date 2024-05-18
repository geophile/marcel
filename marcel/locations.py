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

import os
import pathlib

import marcel.exception
import marcel.object.workspace


# ws_name is the empty string for default workspaces. Default workspaces have a config dir and file,
# and a data dir and history file. But they don't have a workspace properties file, environment file, or
# a marker file. This explains the different handling of ws_name. ws_name is asserted not to be an empty
# string for obtaining the names of files that don't exist for default workspaces.
class Locations(object):

    MARCEL_DIR_NAME = 'marcel'
    WORKSPACE_DIR_NAME = 'workspace'
    BROKEN_WORKSPACE_DIR_NAME = 'broken'
    DEFAULT_WORKSPACE_DIR_NAME = '__DEFAULT__'

    def __init__(self):
        self.home = Locations.normalize_dir(
            'home directory',
            os.environ.get('HOME', None),
            pathlib.Path.home())
        self.config_base = Locations.normalize_dir(
            'application configuration directory (e.g. XDG_CONFIG_HOME)',
            os.environ.get('XDG_CONFIG_HOME', None),
            self.home / '.config')
        self.data_base = Locations.normalize_dir(
            'application data directory (e.g. XDG_DATA_HOME)',
            os.environ.get('XDG_DATA_HOME', None),
            self.home / '.local' / 'share')
        # Record the pid. Process spawning creates children with different pids, but when a pid shows up in
        # a filename, we want the pid of the topmost process.
        self.pid = os.getpid()

    def config_base_path(self):
        return Locations.ensure_dir_exists(self.config_base /
                                           Locations.MARCEL_DIR_NAME)

    def config_workspace_base_path(self):
        return Locations.ensure_dir_exists(self.config_base /
                                           Locations.MARCEL_DIR_NAME /
                                           Locations.WORKSPACE_DIR_NAME)

    def config_broken_workspace_base_path(self):
        return Locations.ensure_dir_exists(self.config_base /
                                           Locations.MARCEL_DIR_NAME /
                                           Locations.BROKEN_WORKSPACE_DIR_NAME)

    def data_base_path(self):
        return Locations.ensure_dir_exists(self.data_base /
                                           Locations.MARCEL_DIR_NAME)

    def data_workspace_base_path(self):
        return Locations.ensure_dir_exists(self.data_base /
                                           Locations.MARCEL_DIR_NAME /
                                           Locations.WORKSPACE_DIR_NAME)

    def data_broken_workspace_base_path(self):
        return Locations.ensure_dir_exists(self.data_base /
                                           Locations.MARCEL_DIR_NAME /
                                           Locations.BROKEN_WORKSPACE_DIR_NAME)

    def config_dir_path(self, workspace):
        return self.config_workspace_base_path() / Locations.workspace_dir_name(workspace)

    def broken_config_dir_path(self, workspace, timestamp):
        return self.config_broken_workspace_base_path() / str(timestamp) / Locations.workspace_dir_name(workspace)

    def data_dir_path(self, workspace):
        return self.data_workspace_base_path() / Locations.workspace_dir_name(workspace)

    def broken_data_dir_path(self, workspace, timestamp):
        return self.data_broken_workspace_base_path() / str(timestamp) / Locations.workspace_dir_name(workspace)

    def reservoir_dir_path(self, workspace):
        return self.data_dir_path(workspace) / 'reservoirs'

    def config_file_path(self, workspace):
        return self.config_dir_path(workspace) / 'startup.py'

    def history_file_path(self, workspace):
        return self.data_dir_path(workspace) / 'history'

    def workspace_properties_file_path(self, workspace):
        assert not workspace.is_default()
        return self.data_dir_path(workspace) / 'properties.pickle'

    def workspace_environment_file_path(self, workspace):
        filename = f'{self.pid}.env.pickle' if workspace.is_default() else 'env.pickle'
        return self.data_dir_path(workspace) / filename

    def reservoir_file_path(self, workspace, name):
        filename = f'{self.pid}.{name}.pickle' if workspace.is_default() else f'{name}.pickle'
        return self.reservoir_dir_path(workspace) / filename

    def version_file_path(self):
        return Locations.ensure_dir_exists(self.config_base /
                                           Locations.MARCEL_DIR_NAME) / 'VERSION'

    def fresh_install(self):
        # Don't rely on Locations.marcel_dir(self.config_base), because it will create .config/marcel if it
        # doesn't exist. Right now, we're just trying to see if it does exist, to guide startup and migration.
        return not (self.config_base / Locations.MARCEL_DIR_NAME).exists()

    @staticmethod
    def ensure_dir_exists(dir):
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

    @staticmethod
    def workspace_dir_name(workspace):
        return Locations.DEFAULT_WORKSPACE_DIR_NAME if workspace.is_default() else workspace.name
