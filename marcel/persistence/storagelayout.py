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
import datetime
import pathlib
import shutil

import marcel.exception
import marcel.locations
import marcel.util


def storage_layout():
    # Check newest first. It is possible that old migrations didn't clean up properly,
    # e.g. original to xdg.
    for layout_class in (StorageLayoutPromptToolkit,
                         StorageLayoutWS3,
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
        self.config = locations.config_base / 'marcel'
        self.data = locations.data_base / 'marcel'

    def __repr__(self):
        return type(self).__name__

    def layout(self):
        assert False, self

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

    def __init__(self):
        super().__init__()

    def layout(self):
        return 'original'

    def migrate(self):
        self.config.mkdir(parents=True, exist_ok=True)
        self.data.mkdir(parents=True, exist_ok=True)
        shutil.move(self.home / '.marcel.py', self.config / 'startup.py')
        shutil.move(self.home / '.marcel_history', self.data / 'history')
        layout = storage_layout()
        assert layout
        assert layout.layout() == 'xdg'
        return layout

    def match(self):
        match = ((self.home / '.marcel.py').exists() and (self.home / '.marcel_history').exists())
        return match


# Version >= ~0.13.6. First use of XDG conventions.
class StorageLayoutXDG(StorageLayout):

    def layout(self):
        return 'xdg'

    def migrate(self):
        (self.config / '.WORKSPACE').touch(mode=0o000)
        (self.data / 'reservoirs').mkdir(exist_ok=True)
        layout = storage_layout()
        assert layout
        assert layout.layout() == 'ws1'
        return layout

    def match(self):
        return (self.config.exists() and
                self.data.exists())


# Version >= 0.20.0. First workspace layout.
class StorageLayoutWS1(StorageLayout):

    def layout(self):
        return 'ws1'

    def migrate(self):
        def fix_default_workspace(base_dir, *filenames):
            new_default_workspace_dir = base_dir / '__DEFAULT_WORKSPACE__'
            new_default_workspace_dir.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                shutil.move(base_dir / filename, new_default_workspace_dir)

        # Move default workspace files to __DEFAULT_WORKSPACE__ directory
        fix_default_workspace(self.config, '.WORKSPACE', 'startup.py')
        fix_default_workspace(self.data, 'history', 'reservoirs')
        layout = storage_layout()
        assert layout
        assert layout.layout() == 'ws2'
        return layout

    def match(self):
        return (self.config.exists() and
                (self.config / '.WORKSPACE').exists())


# Version >= 0.24.0. Default workspace in its own directory.
class StorageLayoutWS2(StorageLayout):

    def layout(self):
        return 'ws2'

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
        layout = storage_layout()
        assert layout
        assert layout.layout() == 'ws3'
        return layout

    def match(self):
        return (self.config.exists() and
                (self.config / '__DEFAULT_WORKSPACE__').exists())


# Version >= 0.28.0. Separate broken and valid workspaces.
class StorageLayoutWS3(StorageLayout):

    def layout(self):
        return 'ws3'

    def migrate(self):
        # Just trash old histories.
        layout = None
        for workspace_dir in StorageLayout.subdirs(self.data / 'workspace'):
            history_file = workspace_dir / 'history'
            history_file.unlink()
            # Write something that looks like a prompt_toolkit history file
            with open(history_file, 'w') as f:
                f.write('\n')
                f.write(datetime.datetime.now().strftime('# %Y-%m-%d %H:%M:%S.%f\n'))
                f.write('+("History from before marcel version 0.32.0 has been deleted, '
                        'due to a change in history file format.")\n')
        layout = storage_layout()
        assert layout
        assert layout.layout() == 'pt'
        return layout

    def match(self):
        return (self.config.exists() and
                (self.config / 'workspace').exists() and
                (self.config / 'workspace' / '__DEFAULT__').exists())

# Version >= 0.32.0. Switch from readline history format to that of prompt_toolkit.
class StorageLayoutPromptToolkit(StorageLayout):

    def layout(self):
        return 'pt'

    def migrate(self):
        return None

    def match(self):
        # Same layout as ws3, but the top of this history file looks like this:
        #
        #     # 2025-04-02 16:54:22.895547
        # Look for a blank line followed by "# 2...-..-.. ..:  :  ."
        #    positions:                      0  3  6  9  12 15 18 21
        # where . is any character
        if not (self.config.exists() and
                (self.config / 'workspace').exists() and
                (self.config / 'workspace' / '__DEFAULT__').exists()):
            return False
        history_file = self.data / 'workspace' / '__DEFAULT__' / 'history'
        if history_file.exists():
            with open(history_file) as f:
                l1 = f.readline().strip()
                l2 = f.readline().strip()
                if (len(l1) == 0 and len(l2) > 0 and
                    l2[:3] == '# 2' and
                    l2[6] == '-' and
                    l2[9] == '-' and
                    l2[12] == ' ' and
                    l2[15] == ':' and
                    l2[18] == ':' and
                    l2[21] == '.'):
                    return True
        return False