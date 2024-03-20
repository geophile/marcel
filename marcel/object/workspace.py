# This file is part of Marcel.
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
import time

import marcel.exception
import marcel.object.renderable
import marcel.reservoir
import marcel.util

WORKSPACE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def format_time(t):
    return time.strftime(WORKSPACE_TIME_FORMAT, time.localtime(t))


class WorkspaceProperties(object):

    def __init__(self):
        self.create_time = time.time()
        self.open_time = self.create_time
        self.save_time = self.create_time
        self.home = None

    def __repr__(self):
        buffer = ['WorkspaceProperties(']
        if self.home:
            buffer.append(f'home = {self.home}')
        buffer.append(f'create = {format_time(self.create_time)}')
        buffer.append(f'open = {format_time(self.open_time)}')
        buffer.append(f'save = {format_time(self.save_time)})')
        return ', '.join(buffer)

    def update_open_time(self):
        self.open_time = time.time()

    def update_save_time(self):
        self.save_time = time.time()

    def set_home(self, home):
        self.home = home


class Workspace(marcel.object.renderable.Renderable):

    _DEFAULT = None

    # Renderable

    def render_full(self, color_scheme):
        return self.render_compact()

    # Workspace

    def is_default(self):
        return False

    def exists(self, env):
        locations = env.locations
        if locations.config_dir_path(self).exists():
            marker_path = locations.workspace_marker_file_path(self)
            return marker_path is not None and marker_path.exists()
        else:
            return False

    def create(self, env, initial_config_contents=None):
        assert initial_config_contents is not None
        if not self.exists(env):
            locations = env.locations
            # config
            config_dir = locations.config_dir_path(self)
            self.create_dir(config_dir)
            config_file_path = locations.config_file_path(self)
            with open(config_file_path, 'w') as config_file:
                config_file.write(initial_config_contents)
            config_file_path.chmod(0o600)
            locations.workspace_marker_file_path(self).touch(mode=0o000, exist_ok=False)
            # data
            self.create_dir(locations.data_dir_path(self))
            self.create_dir(locations.reservoir_dir_path(self))
            locations.history_file_path(self).touch(mode=0o600, exist_ok=False)

    def open(self, env):
        pass

    def close(self, env):
        for _, reservoir in env.reservoirs():
            assert type(reservoir) is marcel.reservoir.Reservoir
            reservoir.close()
            reservoir.ensure_deleted()

    def set_home(self, env, homedir):
        assert False

    @staticmethod
    def default():
        if Workspace._DEFAULT is None:
            Workspace._DEFAULT = WorkspaceDefault()
        return Workspace._DEFAULT

    @staticmethod
    def list(env):
        yield Workspace.default()
        locations = env.locations
        for dir in locations.config_base_path().iterdir():
            if dir.is_dir():
                name = dir.name
                if name != WorkspaceDefault.DIR_NAME:
                    workspace = WorkspaceNamed(name)
                    if locations.workspace_marker_file_path(workspace).exists():
                        workspace.read_properties(env)  # So that home is known
                        yield workspace

    # Internal

    def create_dir(self, dir):
        try:
            dir.mkdir(parents=True)
            assert dir.exists(), dir
        except FileExistsError:
            pass
        except FileNotFoundError:
            raise marcel.exception.KillCommandException(
                f'Workspace name must be usable as a legal filename: {self.name}')


class WorkspaceDefault(Workspace):

    DIR_NAME = '__DEFAULT_WORKSPACE__'

    def __init__(self):
        super().__init__()
        self.env_file = None

    # Renderable

    def render_compact(self):
        return 'Workspace()'

    # Workspace

    @property
    def name(self):
        return ''

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

    def create(self, env, initial_config_contents=None):
        assert initial_config_contents is not None
        super().create(env, initial_config_contents)

    def open(self, env):
        pass

    def close(self, env):
        super().close(env)
        pass

    def set_home(self, env, homedir):
        raise marcel.exception.KillCommandException('Default workspace cannot have a home directory.')


class WorkspaceNamed(Workspace):

    MARKER = '.WORKSPACE'

    def __init__(self, name):
        super().__init__()
        assert name is not None
        self.name = name
        self.properties = None
        self.persistent_state = None

    # Renderable

    def render_compact(self):
        return (f'Workspace({self.name})'
                if self.home() is None else
                f'Workspace({self.name} @ {self.home()})')

    # Workspace

    @property
    def create_time(self):
        return self.properties.create_time

    @property
    def open_time(self):
        return self.properties.open_time

    @property
    def save_time(self):
        return self.properties.save_time

    def create(self, env, initial_config_contents=None):
        assert initial_config_contents is None
        with open(env.locations.config_file_path(Workspace.default()), 'r') as config_file:
            initial_config_contents = config_file.read()
        super().create(env, initial_config_contents)
        self.properties = WorkspaceProperties()
        self.close(env)

    def open(self, env):
        if not self.is_open():
            self.lock_workspace(env.locations)
            self.read_properties(env)
            self.read_environment(env)

    def close(self, env):
        if self.is_open():
            # Properties
            self.write_properties(env)
            # Reservoirs
            for var, reservoir in env.reservoirs():
                assert type(reservoir) is marcel.reservoir.Reservoir
                reservoir.close()
            # Environment (Do this last because env.persistent_state() is destructive.)
            self.write_environment(env)
            # Mark this workspace object as closed
            self.properties = None
            # Unlock
            self.unlock_workspace(env.locations)

    def set_home(self, env, home):
        self.properties.set_home(home)
        self.write_properties(env)

    # WorkspaceNamed

    def delete(self, env):
        assert not self.is_open()  # Caller should have guaranteed this
        locations = env.locations
        self.lock_workspace(locations)
        # Use missing_ok = True to enable deletion of damaged workspaces, missing files.
        # config directory
        locations.workspace_marker_file_path(self).unlink(missing_ok=True)
        locations.config_file_path(self).unlink(missing_ok=True)
        locations.config_dir_path(self).rmdir()
        # data directory
        locations.history_file_path(self).unlink(missing_ok=True)
        locations.workspace_properties_file_path(self).unlink(missing_ok=True)
        locations.workspace_environment_file_path(self).unlink(missing_ok=True)
        reservoir_dir = locations.reservoir_dir_path(self)
        for reservoir_file in reservoir_dir.iterdir():
            reservoir_file.unlink()
        reservoir_dir.rmdir()
        locations.data_dir_path(self).rmdir()

    def home(self):
        # Older workspaces won't have a home property
        return None if self.is_default() or not hasattr(self.properties, 'home') else self.properties.home

    # Internal

    def is_open(self):
        return self.properties is not None

    def lock_workspace(self, locations):
        marker_path = locations.workspace_marker_file_path(self)
        owner = WorkspaceNamed.owner(marker_path)
        if owner is None:
            # Lock the file by renaming it. Check for success, to guard against another process trying to
            # lock the same workspace.
            locked_marker_path = marker_path.parent / f'{WorkspaceNamed.MARKER}.{os.getpid()}'
            marker_path.rename(locked_marker_path)
            if not locked_marker_path.exists():
                self.cannot_lock_workspace()
        elif owner == os.getpid():
            # Already locked
            pass
        else:
            # It's locked by another process
            if marcel.util.process_exists(owner):
                self.cannot_lock_workspace()
            else:
                # Owner disappeared. Rename the file and try again.
                unlocked_marker_path = marker_path.parent / WorkspaceNamed.MARKER
                marker_path.rename(unlocked_marker_path)
                assert unlocked_marker_path.exists(), unlocked_marker_path
                self.lock_workspace(locations)

    def unlock_workspace(self, locations):
        marker_path = locations.workspace_marker_file_path(self)
        owner = WorkspaceNamed.owner(marker_path)
        if owner is None:
            # Someone is unlocking an unlocked workspace? I'll allow it.
            pass
        elif owner == os.getpid():
            # Unlock
            unlocked_marker_path = marker_path.parent / WorkspaceNamed.MARKER
            marker_path.rename(unlocked_marker_path)
            assert unlocked_marker_path.exists(), marker_path
        else:
            # Owned by someone else?!
            assert False, marker_path

    def cannot_lock_workspace(self):
        raise marcel.exception.KillCommandException(f'Workspace {self.name} is in use by another process.')

    def read_properties(self, env):
        with open(env.locations.workspace_properties_file_path(self), 'rb') as properties_file:
            unpickler = dill.Unpickler(properties_file)
            self.properties = unpickler.load()
        self.properties.update_open_time()

    def write_properties(self, env):
        with open(env.locations.workspace_properties_file_path(self), 'wb') as properties_file:
            pickler = dill.Pickler(properties_file)
            pickler.dump(self.properties)
        self.properties.update_save_time()

    def read_environment(self, env):
        with open(env.locations.workspace_environment_file_path(self), 'rb') as environment_file:
            unpickler = dill.Unpickler(environment_file)
            self.persistent_state = unpickler.load()

    def write_environment(self, env):
        with open(env.locations.workspace_environment_file_path(self), 'wb') as environment_file:
            pickler = dill.Pickler(environment_file)
            pickler.dump(env.persistent_state())

    @staticmethod
    def owner(marker_file_path):
        if marker_file_path.name == WorkspaceNamed.MARKER:
            return None
        else:
            assert marker_file_path.name[len(WorkspaceNamed.MARKER)] == '.'
            owner_pid = marker_file_path.name[len(WorkspaceNamed.MARKER) + 1:]
            return int(owner_pid)

