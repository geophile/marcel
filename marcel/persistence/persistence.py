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

import marcel.exception
import marcel.locations
import marcel.object.workspace

Workspace = marcel.object.workspace.Workspace
WorkspaceValidater = marcel.object.workspace.WorkspaceValidater


def validate_all(env, error_handler):
    def check_dir_exists(path, description):
        if not path.exists():
            raise marcel.exception.KillShellException(
                f'{description} directory missing.')
        if not path.is_dir():
            raise marcel.exception.KillShellException(
                f'{description} directory is not actually a directory.')

    def check_file_exists(path, description):
        if not path.exists():
            raise marcel.exception.KillShellException(
                f'{description} file missing.')
        if not path.is_file():
            raise marcel.exception.KillShellException(
                f'{description} is not actually a file.')

    def workspace_named(name):
        return (Workspace.default()
                if name == env.locations.DEFAULT_WORKSPACE_DIR_NAME else
                Workspace(name))

    locations = env.locations
    errors = []
    # Version
    check_file_exists(locations.config_version(), 'VERSION')
    # Config dir has broken/, workspace/ and nothing else.
    check_dir_exists(locations.config_ws(), 'Workspace configuration')
    check_dir_exists(locations.config_bws(), 'Broken workspace configuration')
    # Data dir has broken/, workspace/ and nothing else.
    check_dir_exists(locations.data_ws(), 'Workspace data')
    check_dir_exists(locations.data_bws(), 'Broken workspace data')
    # The data and config workspace directories should have subdirectories with matching names.
    config_workspace_names = set([f.name for f in locations.config_ws().iterdir()])
    data_workspace_names = set([f.name for f in locations.data_ws().iterdir()])
    broken_workspace_names = set()
    for missing_data_dir in (config_workspace_names - data_workspace_names):
        broken = Workspace(missing_data_dir)
        broken_workspace_names.add(broken.name)
        errors.append(WorkspaceValidater.Error(broken.name, f'{locations.data_ws(broken)} is missing'))
    for missing_config_dir in (data_workspace_names - config_workspace_names):
        broken = Workspace(missing_config_dir)
        broken_workspace_names.add(broken.name)
        errors.append(WorkspaceValidater.Error(broken.name, f'{locations.config_ws(broken)} is missing'))
    # Validate each workspace. Don't rely on Workspace.list(), which assumes valid workspaces.
    # E.g., a missing marker file will cause the broken workspace to not be included in the output.
    for dir in locations.config_ws().iterdir():
        if dir.name in data_workspace_names:
            workspace = workspace_named(dir.name)
            ws_errors = workspace.validate(env)
            if len(ws_errors) > 0:
                broken_workspace_names.add(dir.name)
                errors.extend(ws_errors)
        # else: Missing data workspace directory has already been noted.
    error_handler(broken_workspace_names, errors)
    return errors
