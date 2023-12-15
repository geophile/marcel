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

import dill
import os
import shutil
import time

import marcel.exception
import marcel.object.renderable

WORKSPACE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def format_time(t):
    return time.strftime(WORKSPACE_TIME_FORMAT, time.localtime(t))


class WorkspaceProperties(object):

    def __init__(self):
        self.create_time = time.time()
        self.open_time = self.create_time
        self.save_time = self.create_time

    def __repr__(self):
        return (f'WorkspaceProperties('
                f'create = {format_time(self.create_time)}, '
                f'open = {format_time(self.open_time)}, '
                f'save = {format_time(self.save_time)})')

    def update_open_time(self):
        self.open_time = time.time()

    def update_save_time(self):
        self.save_time = time.time()


class WorkspaceDefault(marcel.object.renderable.Renderable):

    def __init__(self):
        self.name = ''

    def __repr__(self):
        return self.render_compact()

    # Renderable

    def render_compact(self):
        return f'Workspace({self.name})'

    def render_full(self, color_scheme):
        return self.render_compact()

    # WorkspaceDefault

    @property
    def create_time(self):
        return None

    @property
    def open_time(self):
        return None

    @property
    def save_time(self):
        return None

    def is_default(self):
        return True

    def is_open(self):
        return True

    def exists(self, env):
        return True

    def create(self, env):
        assert False

    def open(self, env):
        pass

    def close(self, env):
        pass


class Workspace(WorkspaceDefault):

    DEFAULT = WorkspaceDefault()
    MARKER = '.WORKSPACE'

    def __init__(self, name):
        super().__init__()
        assert name is not None
        self.name = name
        self.properties = None
        self.persistent_state = None

    # Renderable

    def render_compact(self):
        return f'Workspace({self.name})'

    def render_full(self, color_scheme):
        wp = self.properties
        return (f'Workspace({self.name}, '
                f'create_time = {format_time(wp.create_time)}, '
                f'open_time = {format_time(wp.open_time)}, '
                f'save_time = {format_time(wp.save_time)})')

    # WorkspaceDefault

    @property
    def create_time(self):
        return self.properties.create_time

    @property
    def open_time(self):
        return self.properties.open_time

    @property
    def save_time(self):
        return self.properties.save_time

    def is_default(self):
        return False

    def is_open(self):
        return self.properties is not None

    def exists(self, env):
        locations = env.locations
        if locations.config_dir_path(self.name).exists():
            marker_path = locations.workspace_marker_file_path(self.name)
            return marker_path is not None and marker_path.exists()
        else:
            return False

    def create(self, env):
        locations = env.locations
        # config
        config_dir = locations.config_dir_path(self.name)
        self.create_dir(config_dir)
        shutil.copyfile(locations.config_file_path(Workspace.DEFAULT.name), locations.config_file_path(self.name))
        locations.workspace_marker_file_path(self.name).touch(mode=0o000, exist_ok=False)
        # history
        history_dir = locations.data_dir_path(self.name)
        self.create_dir(history_dir)
        locations.history_file_path(self.name).touch(mode=0o600, exist_ok=False)
        self.properties = WorkspaceProperties()
        self.close(env)  # Saves properties and environment

    def open(self, env):
        if not self.is_open():
            locations = env.locations
            self.lock_workspace(locations)
            # Properties
            with open(locations.workspace_properties_file_path(self.name), 'rb') as properties_file:
                unpickler = dill.Unpickler(properties_file)
                self.properties = unpickler.load()
            # Environment
            with open(locations.workspace_environment_file_path(self.name), 'rb') as environment_file:
                unpickler = dill.Unpickler(environment_file)
                self.persistent_state = unpickler.load()
            self.properties.update_open_time()

    def close(self, env):
        if self.is_open():
            self.properties.update_save_time()
            locations = env.locations
            # Properties
            with open(locations.workspace_properties_file_path(self.name), 'wb') as properties_file:
                pickler = dill.Pickler(properties_file)
                pickler.dump(self.properties)
            # Environment
            with open(locations.workspace_environment_file_path(self.name), 'wb') as environment_file:
                pickler = dill.Pickler(environment_file)
                pickler.dump(env.persistent_state())
            # Mark this workspace object as closed
            self.properties = None
            # Unlock
            self.unlock_workspace(locations)

    @staticmethod
    def list(env):
        yield Workspace.DEFAULT
        locations = env.locations
        for dir in locations.config_dir_path(Workspace.DEFAULT.name).iterdir():
            name = dir.name
            if dir.is_dir() and locations.workspace_marker_file_path(name).exists():
                workspace = Workspace(name)
                with open(locations.workspace_properties_file_path(name), 'rb') as properties_file:
                    pickler = dill.Unpickler(properties_file)
                    workspace.properties = pickler.load()
                    yield workspace

    # Internal

    def create_dir(self, dir):
        try:
            os.mkdir(dir)
            assert dir.exists(), dir
        except FileExistsError:
            raise marcel.exception.KillCommandException(
                f'Workspace {self.name} already exists.')
        except FileNotFoundError:
            raise marcel.exception.KillCommandException(
                f'Workspace name must be usable as a legal filename: {self.name}')

    def lock_workspace(self, locations):
        marker_path = locations.workspace_marker_file_path(self.name)
        owner = Workspace.owner(marker_path)
        if owner is None:
            # Lock the file by renaming it. Check for success, to guard against another process trying to
            # lock the same workspace.
            locked_marker_path = marker_path.parent / f'{Workspace.MARKER}.{os.getpid()}'
            marker_path.rename(locked_marker_path)
            if not locked_marker_path.exists():
                self.cannot_lock_workspace()
        elif owner == os.getpid():
            # Already locked
            pass
        else:
            # It's locked by another process
            self.cannot_lock_workspace()

    def unlock_workspace(self, locations):
        marker_path = locations.workspace_marker_file_path(self.name)
        owner = Workspace.owner(marker_path)
        if owner is None:
            # Someone is unlocking an unlocked workspace? I'll allow it.
            pass
        elif owner == os.getpid():
            # Unlock
            unlocked_marker_path = marker_path.parent / Workspace.MARKER
            marker_path.rename(unlocked_marker_path)
            if not unlocked_marker_path.exists():
                assert False, marker_path
        else:
            # Owned by someone else?!
            assert False, marker_path

    def cannot_lock_workspace(self):
        raise marcel.exception.KillCommandException(f'Workspace {self.name} is in use by another process.')

    @staticmethod
    def owner(marker_file_path):
        if marker_file_path.name == Workspace.MARKER:
            return None
        else:
            assert marker_file_path.name[len(Workspace.MARKER)] == '.'
            owner_pid = marker_file_path.name[len(Workspace.MARKER) + 1:]
            return int(owner_pid)

