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

# Directory layout before v0.24:
#
# XDG_CONFIG_HOME/ (normally .config/marcel/)
#     startup.py  # For default workspace, and template for named
#     .WORKSPACE  # Marker for default workspace
#     WORKSPACE_NAME/
#         startup.py
#         .WORKSPACE  # Empty file marking this directory as a workspace
#
# XDG_DATA_HOME/ (normally .local/share/marcel/)
#     history
#     reservoirs/  # For default workspace
#         <pid>.<varname>.pickle  # Deleted at end of session
#     WORKSPACE_NAME/
#         env.pickle
#         history
#         properties.pickle
#         reservoirs/
#             <varname>.pickle
#
# Directory layout for v0.24:
#
# XDG_CONFIG_HOME/ (normally .config/marcel/)
#     VERSION  # Contains full (3-part) version number
#     __DEFAULT_WORKSPACE__
#         startup.py  # For default workspace, and template for named
#         .WORKSPACE  # Marker for default workspace
#     WORKSPACE_NAME/
#         startup.py
#         .WORKSPACE  # Empty file marking this directory as a workspace
#
# XDG_DATA_HOME/ (normally .local/share/marcel/)
#     __DEFAULT_WORKSPACE__
#         history
#         reservoirs/  # For default workspace
#             <pid>.<varname>.pickle  # Deleted at end of session
#     WORKSPACE_NAME/
#         env.pickle
#         history
#         properties.pickle
#         reservoirs/
#             <varname>.pickle

import shutil

import marcel.exception
import marcel.version
from marcel.object.workspace import Workspace


def should_not_exist(path):
    if path.exists():
        raise marcel.exception.KillShellException(f'Did not expect {path} to exist.')


def migrate(locations):
    # Create VERSION file. (Caller will fill in the value.)
    version_file_path = locations.version_file_path()
    should_not_exist(version_file_path)
    version_file_path.touch(mode=0o400, exist_ok=True)  # Allow for race
    # config __DEFAULT_WORKSPACE__
    default_workspace = Workspace.default()
    config_dir_path = locations.config_dir_path(default_workspace)
    should_not_exist(config_dir_path)
    try:
        config_dir_path.mkdir(parents=True, exist_ok=False)
        config_dir_path_old = config_dir_path.parent
        shutil.move(config_dir_path_old / 'startup.py', config_dir_path)
        shutil.move(config_dir_path_old / '.WORKSPACE', config_dir_path)
    except FileExistsError:
        # Must be a race with another process also doing migration
        pass
    # data __DEFAULT_WORKSPACE__
    data_dir_path = locations.data_dir_path(default_workspace)
    should_not_exist(data_dir_path)
    try:
        data_dir_path.mkdir(parents=True, exist_ok=False)
        data_dir_path_old = data_dir_path.parent
        shutil.move(data_dir_path_old / 'history', data_dir_path)
        shutil.move(data_dir_path_old / 'reservoirs', data_dir_path)
    except FileExistsError:
        # Must be a race with another process also doing migration
        pass
