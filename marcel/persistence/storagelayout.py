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

import pathlib
import shutil

import marcel.exception
import marcel.locations


def storage_layout():
    # Check newest first. It is possible that old migrations didn't clean up properly,
    # e.g. original to xdg.
    for layout_class in (StorageLayoutWS3,
                         StorageLayoutWS2,
                         StorageLayoutWS1,
                         StorageLayoutXDG,
                         StorageLayoutOriginal):
        layout = layout_class()
        if layout.match():
            return layout
    return None


class StorageLayout(object):

    def __init__(self):
        # Can't rely on Locations for directory and file locations, since those would
        # represent current version only. But home and XDG analysis in Locations.__init__
        # is useful.
        locations = marcel.locations.Locations()
        self.home = locations.home
        self.config = locations.config_base
        self.data = locations.data_base

    def __repr__(self):
        return type(self).__name__

    def migrate(self):
        assert False

    def should_exist(self, path, info):
        if not path.exists():
            raise marcel.exception.KillShellException(
                f'Migration({type(self)}) error: {path} should exist: {info}')

    def should_not_exist(self, path, info):
        if path.exists():
            raise marcel.exception.KillShellException(
                f'Migration({type(self)}) error: {path} should not exist: {info}')

    @staticmethod
    def subdirs(dir):
        workspace_dirs = []
        for path in dir.iterdir():
            if path.is_dir():
                workspace_dirs.append(path)
        return workspace_dirs


# Version < 0.13.6
class StorageLayoutOriginal(StorageLayout):

    def migrate(self):
        pass

    def match(self):
        return ((self.home / '.marcel').exists() and
                (self.home / '.marcel_history').exists())


# Version >= ~0.13.6. First use of XDG conventions.
class StorageLayoutXDG(StorageLayout):

    def migrate(self):
        pass

    def match(self):
        return (self.config.exists() and
                self.data.exists())


# Version >= 0.20.0. First workspace layout.
class StorageLayoutWS1(StorageLayout):

    def migrate(self):
        pass

    def match(self):
        return (self.config.exists() and
                (self.config / '.WORKSPACE').exists())


# Version >= 0.24.0. Default workspace in its own directory.
class StorageLayoutWS2(StorageLayout):

    def migrate(self):
        def move_workspace_dirs(workspace_dirs, new_workspace_base):
            for workspace_dir in workspace_dirs:
                if workspace_dir.name != marcel.locations.Locations.WORKSPACE_DIR_NAME:
                    moved_dir = shutil.move(workspace_dir, new_workspace_base)
                    if moved_dir:
                        self.should_exist(pathlib.Path(moved_dir), f'Tried to move workspace dir {workspace_dir}')
                    else:
                        raise marcel.exception.KillShellException(
                            f'Attempt to move workspace dir {workspace_dir} failed.')
                    self.should_not_exist(workspace_dir, f'Tried to move workspace dir {workspace_dir}')

        def fix_dirs(base_dir):
            new_workspace_dir = base_dir / 'workspace'
            new_workspace_dir.mkdir(parents=True, exist_ok=True)
            # Move workspace directories
            old_workspace_dirs = StorageLayout.subdirs(base_dir)
            move_workspace_dirs(old_workspace_dirs, new_workspace_dir)
            # Rename __DEFAULT_WORKSPACE__ to __DEFAULT__
            old_default_workspace_dir = new_workspace_dir / '__DEFAULT_WORKSPACE__'
            new_default_workspace_dir = new_workspace_dir / '__DEFAULT__'
            old_default_workspace_dir.rename(new_default_workspace_dir)
            # Create dir for broken workspaces
            new_broken_dir = base_dir / 'broken'
            new_broken_dir.mkdir(parents=False, exist_ok=False)

        fix_dirs(self.config)
        fix_dirs(self.data)
        migrated = storage_layout()
        if type(migrated) is not StorageLayoutWS3:
            raise marcel.exception.KillShellException('Migration from ws2 layout to ws3 failed.')
        migrated.migrate()

    def match(self):
        return (self.config.exists() and
                (self.config / '__DEFAULT_WORKSPACE__').exists())


# Version >= 0.28.0. Separate broken and valid workspaces.
class StorageLayoutWS3(StorageLayout):

    def migrate(self):
        pass

    def match(self):
        return (self.config.exists() and
                (self.config / 'workspace').exists() and
                (self.config / 'workspace' / '__DEFAULT__').exists())
