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
import pathlib
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

    _MARKER = '.WORKSPACE'
    _DEFAULT = None

    def __init__(self, name):
        assert name is not None
        self.name = name
        self.properties = None
        self.persistent_state = None

    # Renderable

    def render_compact(self):
        return (f'Workspace({self.name})'
                if self.home() is None else
                f'Workspace({self.name} @ {self.home()})')

    def render_full(self, color_scheme):
        return self.render_compact()

    # Workspace

    def is_default(self):
        return False

    def exists(self, env):
        locations = env.locations
        return self.any_marker_exists(env) if locations.config_dir_path(self).exists() else False

    def create(self, env):
        assert not self.exists(env)
        locations = env.locations
        with open(locations.config_file_path(Workspace.default()), 'r') as config_file:
            initial_config_contents = config_file.read()
        self.create_on_disk(env, initial_config_contents)

    def open(self, env):
        if not self.is_open(env):
            self.lock_workspace(env.locations)
            self.read_properties(env)
            self.read_environment(env)

    def close(self, env, restart):
        if self.is_open(env):
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
        home = pathlib.Path(home).absolute()
        self.properties.set_home(home)
        self.write_properties(env)

    def delete(self, env):
        assert not self.is_open(env)  # Caller should have guaranteed this
        locations = env.locations
        self.lock_workspace(locations)
        # Use missing_ok = True to enable deletion of damaged workspaces, missing files.
        # config directory
        locations.workspace_owned_marker_file_path(self).unlink(missing_ok=True)
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
                    workspace = Workspace(name)
                    if workspace.any_marker_exists(env):
                        workspace.read_properties(env)  # So that home is known
                        yield workspace

    # Internal

    def create_on_disk(self, env, initial_config_contents):
        locations = env.locations
        # config
        config_dir = locations.config_dir_path(self)
        self.create_dir(config_dir)
        config_file_path = locations.config_file_path(self)
        with open(config_file_path, 'w') as config_file:
            config_file.write(initial_config_contents)
        config_file_path.chmod(0o600)
        locations.workspace_unowned_marker_file_path(self).touch(mode=0o000, exist_ok=False)
        # data
        self.create_dir(locations.data_dir_path(self))
        self.create_dir(locations.reservoir_dir_path(self))
        self.write_environment(env)
        if not self.is_default():
            self.properties = WorkspaceProperties()
            self.write_properties(env)
        locations.history_file_path(self).touch(mode=0o600, exist_ok=False)

    def create_dir(self, dir):
        try:
            dir.mkdir(parents=True)
            assert dir.exists(), dir
        except FileExistsError:
            pass
        except FileNotFoundError:
            raise marcel.exception.KillCommandException(
                f'Workspace name must be usable as a legal filename: {self.name}')

    # Checks for owned and unowned marker files
    def any_marker_exists(self, env):
        locations = env.locations
        return (locations.workspace_owned_marker_file_path(self).exists() or
                locations.workspace_unowned_marker_file_path(self).exists())

    # A workspace is considered open if it's locked or shared marker file is owned by this process.
    def is_open(self, env):
        return env.locations.workspace_owned_marker_file_path(self).exists()

    def share_workspace(self, locations):
        assert self.is_default()
        # exist_ok = True: We could be returning to the default workspace, previously opened in this process.
        locations.workspace_owned_marker_file_path(self).touch(mode=0o000, exist_ok=True)

    def unshare_workspace(self, locations):
        assert self.is_default()
        locations.workspace_owned_marker_file_path(self).unlink(missing_ok=True)

    def lock_workspace(self, locations):
        assert not self.is_default()
        owner = self.owner(locations)
        if owner is None:
            # Lock the file by renaming it. Check for success, to guard against another process trying to
            # lock the same workspace.
            owned_marker_path = locations.workspace_owned_marker_file_path(self)
            unowned_marker_path = locations.workspace_unowned_marker_file_path(self)
            unowned_marker_path.rename(owned_marker_path)
            if not owned_marker_path.exists():
                self.cannot_lock_workspace()
        elif owner == locations.pid:  # locations.pid is the pid of the topmost process
            # Already locked
            pass
        else:
            # It's locked by another process
            if marcel.util.process_exists(owner):
                self.cannot_lock_workspace()
            else:
                # Owner disappeared. Steal the marker file.
                abandoned_marker_path = locations.workspace_marker_file_path(self) / f'{Workspace._MARKER}.{owner}'
                owned_marker_path = locations.workspace_owned_marker_file_path(self)
                abandoned_marker_path.rename(owned_marker_path)
                if not owned_marker_path.exists():
                    # Another process trying to steal at exactly the same time?!
                    self.cannot_lock_workspace()

    def unlock_workspace(self, locations):
        assert not self.is_default()
        owner = self.owner(locations)
        if owner is None:
            # Someone is unlocking an unlocked workspace? I'll allow it.
            pass
        elif owner == locations.pid:  # locations.pid is the pid of the topmost process
            # Unlock
            owned_marker_path = locations.workspace_owned_marker_file_path(self)
            unowned_marker_path = locations.workspace_unowned_marker_file_path(self)
            owned_marker_path.rename(unowned_marker_path)
            assert unowned_marker_path.exists(), self
        else:
            # Owned by someone else?!
            assert False, self

    def cannot_lock_workspace(self):
        raise marcel.exception.KillCommandException(f'Workspace {self.name} is in use by another process.')

    def read_properties(self, env):
        assert not self.is_default()
        with open(env.locations.workspace_properties_file_path(self), 'rb') as properties_file:
            unpickler = dill.Unpickler(properties_file)
            self.properties = unpickler.load()
        self.properties.update_open_time()

    def write_properties(self, env):
        assert not self.is_default()
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

    # Return pid of owning process, or None if unowned.
    def owner(self, locations):
        # Should only need this for named workspaces.
        assert not self.is_default()
        if locations.workspace_unowned_marker_file_path(self).exists():
            return None
        marker_dir = locations.workspace_owned_marker_file_path(self).parent
        marker_filename = None
        for file in marker_dir.iterdir():
            if file.name.startswith(Workspace._MARKER):
                if marker_filename is None:
                    marker_filename = file.name
                else:
                    assert False, f'Multiple marker files in {marker_dir}'
        assert marker_filename is not None
        return Workspace.marker_filename_pid(marker_filename)

    @staticmethod
    def marker_filename_pid(marker_filename):
        assert marker_filename.startswith(Workspace._MARKER)
        return int(marker_filename[marker_filename.rfind('.') + 1:])


class WorkspaceDefault(Workspace):
    DIR_NAME = '__DEFAULT_WORKSPACE__'

    def __init__(self):
        super().__init__('')

    # Workspace

    def is_default(self):
        return True

    def open(self, env):
        self.share_workspace(env.locations)
        self.read_environment(env)

    def close(self, env, restart):
        # Reservoirs
        for var, reservoir in env.reservoirs():
            assert type(reservoir) is marcel.reservoir.Reservoir
            reservoir.close()
            if not restart:
                reservoir.ensure_deleted()
        # Environment (Do this last because env.persistent_state() is destructive.)
        if restart:
            self.write_environment(env)
        else:
            env.locations.workspace_environment_file_path(self).unlink(missing_ok=True)
        self.unshare_workspace(env.locations)

    def set_home(self, env, homedir):
        raise marcel.exception.KillCommandException('Default workspace does not have a home directory.')

    # WorkspaceDefault

    def ensure_exists(self, env, initial_config_contents):
        assert initial_config_contents is not None
        if not self.exists(env):
            self.create_on_disk(env, initial_config_contents)

    # Internal

    def read_environment(self, env):
        try:
            super().read_environment(env)
        except FileNotFoundError:
            # This can happen on startup when the default workspace for this process hasn't been saved yet.
            # EnvironmentScript.restore_persistent_state_from_workspace defines what keys should be in persistent_state.
            self.persistent_state = {
                'namespace': {},
                'imports': []
            }
