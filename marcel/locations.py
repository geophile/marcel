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


# Location structure -> interface
# 
#     .config/marcel/                             config()
#         VERSION                                 config_version()
#         broken                                  config_bws()
#             <timestamp>/                        
#                 <workspace dirs>                config_bws(workspace, timestamp)
#         workspace                               config_ws()
#             __DEFAULT__/                        config_ws(workspace)
#                 .WORKSPACE
#                 startup.py                      config_ws_startup(workspace)
#             WORKSPACE_NAME/                     config_ws(workspace)
#                 .WORKSPACE
#                 startup.py                      config_ws_startup(workspace)
#
#     .local/share/marcel/                        data()
#         broken                                  data_bws()
#             <timestamp>/                        
#                 <workspace dirs>                data_bws(workspace, timestamp)
#         workspace                               data_ws()
#             __DEFAULT__/                        data_ws(workspace)
#                 <pid>.env.pickle                data_ws_env(workspace)
#                 history                         data_ws_hist(workspace)
#                 reservoirs/                     data_ws_res(workspace)
#                     <pid>.<varname>.pickle      data_ws_res(workspace, name)
#             WORKSPACE_NAME/                     data_ws(workspace)
#                 properties.pickle               data_ws_prop(workspace)
#                 env.pickle                      data_ws_env(workspace)
#                 history                         data_ws_hist(workspace)
#                 reservoirs/                     data_ws_res(workspace)
#                     <varname>.pickle            data_ws_res(workspace, name)

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

    def config(self):
        return Locations.ensure_dir_exists(self.config_base /
                                           Locations.MARCEL_DIR_NAME)

    def config_version(self):
        return Locations.ensure_dir_exists(self.config_base /
                                           Locations.MARCEL_DIR_NAME) / 'VERSION'

    def config_ws(self, workspace=None):
        ws_dir = Locations.ensure_dir_exists(
            self.config_base
            / Locations.MARCEL_DIR_NAME
            / Locations.WORKSPACE_DIR_NAME)
        if workspace:
            ws_dir = ws_dir / Locations.workspace_dir_name(workspace)
        return ws_dir

    def config_bws(self, workspace=None, timestamp=None):
        assert (workspace is None) == (timestamp is None)
        bws_dir = Locations.ensure_dir_exists(
            self.config_base
            / Locations.MARCEL_DIR_NAME
            / Locations.BROKEN_WORKSPACE_DIR_NAME)
        if workspace is not None and timestamp is not None:
            bws_dir = bws_dir / str(timestamp) / Locations.workspace_dir_name(workspace)
        return Locations.ensure_dir_exists(bws_dir)

    def config_ws_startup(self, workspace):
        return self.config_ws(workspace) / 'startup.py'

    def data(self):
        return Locations.ensure_dir_exists(self.data_base /
                                           Locations.MARCEL_DIR_NAME)

    def data_ws(self, workspace=None):
        ws_dir = Locations.ensure_dir_exists(
            self.data_base /
            Locations.MARCEL_DIR_NAME /
            Locations.WORKSPACE_DIR_NAME)
        if workspace:
            ws_dir = ws_dir / Locations.workspace_dir_name(workspace)
        return ws_dir

    def data_bws(self, workspace=None, timestamp=None):
        assert (workspace is None) == (timestamp is None)
        bws_dir = Locations.ensure_dir_exists(
            self.data_base /
            Locations.MARCEL_DIR_NAME /
            Locations.BROKEN_WORKSPACE_DIR_NAME)
        if workspace is not None and timestamp is not None:
            bws_dir = bws_dir / str(timestamp) / Locations.workspace_dir_name(workspace)
        return Locations.ensure_dir_exists(bws_dir)

    def data_ws_prop(self, workspace):
        assert not workspace.is_default()
        return self.data_ws(workspace) / 'properties.pickle'

    def data_ws_env(self, workspace):
        filename = f'{self.pid}.env.pickle' if workspace.is_default() else 'env.pickle'
        return self.data_ws(workspace) / filename

    def data_ws_hist(self, workspace):
        return self.data_ws(workspace) / 'history'

    def data_ws_res(self, workspace, name=None):
        res_dir = self.data_ws(workspace) / 'reservoirs'
        if name:
            filename = f'{self.pid}.{name}.pickle' if workspace.is_default() else f'{name}.pickle'
            res_dir = res_dir / filename
        return res_dir

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
