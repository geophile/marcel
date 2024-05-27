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

# Directory layout before v0.28.0:
#
#     XDG_CONFIG_HOME/ (normally .config/marcel/)
#         __DEFAULT_WORKSPACE__
#             .WORKSPACE
#             startup.py
#         WORKSPACE_NAME/
#             .WORKSPACE  # Empty file marking this directory as a workspace
#             startup.py
#
#     XDG_DATA_HOME/ (normally .local/share/marcel/)
#         __DEFAULT_WORKSPACE__
#             <pid>.env.pickle  # Deleted on non-restart shutdown
#             history
#             reservoirs/
#                 <pid>.<varname>.pickle  # Deleted on non-restart shutdown
#         WORKSPACE_NAME/
#             env.pickle
#             history
#             properties.pickle
#             reservoirs/
#                 <varname>.pickle
#
# Directory layout starting with v0.28.0:
#
#     XDG_CONFIG_HOME/ (normally .config/marcel/)
#         VERSION  # Contains full (3-part) version number
#         broken/
#             <broken workspace dirs>
#         workspace/
#             __DEFAULT__
#                 .WORKSPACE  # Marker for default workspace
#                 startup.py  # For default workspace, and template for named
#             WORKSPACE_NAME/
#                 .WORKSPACE  # Empty file marking this directory as a workspace
#                 startup.py
#
#     XDG_DATA_HOME/ (normally .local/share/marcel/)
#         broken/
#             <broken workspace dirs>
#         workspace/
#             __DEFAULT__
#                 history
#                 reservoirs/  # For default workspace
#                     <pid>.<varname>.pickle  # Deleted at end of session
#             WORKSPACE_NAME/
#                 env.pickle
#                 history
#                 properties.pickle
#                 reservoirs/
#                     <varname>.pickle

import pathlib
import shutil
import tempfile

import marcel.exception
import marcel.version


def should_not_exist(path):
    if path.exists():
        raise marcel.exception.KillShellException(
            f'Migration(0.28) error: {path} should not still exist! It should have been moved.')


def migrate(locations):
    # broken and workspace dirs are created as temp dirs, and then moved into position.
    # This is to avoid problems migrating workspaces named 'broken' or 'workspace'.

    def subdirs(dir):
        # It should be the case that all directories inside dir are workspace directories
        # (although possibly broken).
        workspace_dirs = []
        for path in dir.iterdir():
            if path.is_dir():
                workspace_dirs.append(path)
        return workspace_dirs

    def move_workspace_dirs(workspace_dirs, new_workspace_base):
        for workspace_dir in workspace_dirs:
            shutil.move(workspace_dir, new_workspace_base)
            should_not_exist(workspace_dir)

    def rename_default_workspace_dir(workspace_dir_path):
        old_default_dir = workspace_dir_path / '__DEFAULT_WORKSPACE__'
        old_default_dir.rename(old_default_dir.parent / '__DEFAULT__')
        should_not_exist(old_default_dir)

    def migrate_config():
        # Get the workspace dirs
        config_base = locations.config()  # .config/marcel
        workspace_dirs = subdirs(config_base)
        # Create broken and workspace directories
        tmp_broken_dir_path = pathlib.Path(tempfile.TemporaryDirectory(dir=config_base).name)
        tmp_workspace_dir_path = pathlib.Path(tempfile.TemporaryDirectory(dir=config_base).name)
        tmp_broken_dir_path.mkdir(parents=True, exist_ok=False)
        tmp_workspace_dir_path.mkdir(parents=True, exist_ok=False)
        # Move workspace directories
        move_workspace_dirs(workspace_dirs, tmp_workspace_dir_path)
        # Rename __DEFAULT_WORKSPACE__ to __DEFAULT__
        rename_default_workspace_dir(tmp_workspace_dir_path)
        # Rename new directories to their permanent names
        tmp_workspace_dir_path.rename(config_base / 'workspace')
        tmp_broken_dir_path.rename(config_base / 'broken')

    def migrate_data():
        # Get the workspace dirs
        data_base = locations.data()  # .local/share/marcel
        workspace_dirs = subdirs(data_base)
        # Create broken and workspace directories
        tmp_broken_dir_path = pathlib.Path(tempfile.TemporaryDirectory(dir=data_base).name)
        tmp_workspace_dir_path = pathlib.Path(tempfile.TemporaryDirectory(dir=data_base).name)
        tmp_broken_dir_path.mkdir(parents=True, exist_ok=False)
        tmp_workspace_dir_path.mkdir(parents=True, exist_ok=False)
        # Move workspace directories
        move_workspace_dirs(workspace_dirs, tmp_workspace_dir_path)
        # Rename __DEFAULT_WORKSPACE__ to __DEFAULT__
        rename_default_workspace_dir(tmp_workspace_dir_path)
        # Rename new directories to their permanent names
        tmp_workspace_dir_path.rename(data_base / 'workspace')
        tmp_broken_dir_path.rename(data_base / 'broken')

    migrate_config()
    migrate_data()

