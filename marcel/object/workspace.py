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
import shutil

import dill
import pathlib
import sys
import time

import marcel.exception
import marcel.locations
import marcel.object.renderable
import marcel.reservoir
import marcel.util

WORKSPACE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class Marker(object):
    FILENAME_ROOT = '.WORKSPACE'

    def __init__(self, workspace):
        self.workspace = workspace

    def exists(self, env):
        locations = env.locations
        config_dir = locations.config_dir_path(self.workspace)
        if config_dir.exists():
            for file in config_dir.iterdir():
                if file.name.startswith(Marker.FILENAME_ROOT):
                    return True
        return False

    def unowned(self, env):
        return env.locations.config_dir_path(self.workspace) / Marker.FILENAME_ROOT

    def owned(self, env, pid=None):
        if pid is None:
            pid = env.locations.pid
        return env.locations.config_dir_path(self.workspace) / f'{Marker.FILENAME_ROOT}.{pid}'


class WorkspaceProperties(object):

    @staticmethod
    def format_time(t):
        return time.strftime(WORKSPACE_TIME_FORMAT, time.localtime(t))

    def __init__(self):
        self.create_time = time.time()
        self.open_time = self.create_time
        self.save_time = self.create_time
        self.home = None

    def __repr__(self):
        buffer = ['WorkspaceProperties(']
        if self.home:
            buffer.append(f'home = {self.home}')
        buffer.append(f'create = {WorkspaceProperties.format_time(self.create_time)}')
        buffer.append(f'open = {WorkspaceProperties.format_time(self.open_time)}')
        buffer.append(f'save = {WorkspaceProperties.format_time(self.save_time)})')
        return ', '.join(buffer)

    def update_open_time(self):
        self.open_time = time.time()

    def update_save_time(self):
        self.save_time = time.time()

    def set_home(self, home):
        self.home = home


class Workspace(marcel.object.renderable.Renderable):
    DEFAULT = None

    def __init__(self, name):
        assert name is not None
        self.name = name
        self.properties = None
        self.persistent_state = None
        self.marker = Marker(self)

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
        return self.marker.exists(env)

    def create(self, env):
        assert not self.exists(env)
        locations = env.locations
        with open(locations.config_file_path(Workspace.default()), 'r') as config_file:
            initial_config_contents = config_file.read()
        self.create_on_disk(env, initial_config_contents)

    def open(self, env):
        if self.exists(env):
            if self.lock_workspace(env):
                self.read_properties(env)
                self.read_environment(env)
            else:
                self.cannot_lock_workspace()
        else:
            self.does_not_exist()

    def close(self, env, restart):
        # Relocking is okay, so this is a convenient way to test that the workspace is locked.
        if self.lock_workspace(env):
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
            self.unlock_workspace(env)
        else:
            assert False, self

    def set_home(self, env, home):
        home = pathlib.Path(home).absolute()
        self.properties.set_home(home)
        self.write_properties(env)

    def delete(self, env):
        if self.exists(env):
            if self.lock_workspace(env):
                locations = env.locations
                # config directory
                # Use missing_ok = True to enable deletion of damaged workspaces, missing files.
                owned_marker_path = self.marker.owned(env)
                assert owned_marker_path is not None, self
                owned_marker_path.unlink(missing_ok=False)
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
            else:
                self.cannot_lock_workspace()
        else:
            self.does_not_exist()

    def home(self):
        # Older workspaces won't have a home property
        return None if self.is_default() or not hasattr(self.properties, 'home') else self.properties.home

    @staticmethod
    def default():
        if Workspace.DEFAULT is None:
            Workspace.DEFAULT = WorkspaceDefault()
        return Workspace.DEFAULT

    @staticmethod
    def list(env):
        yield Workspace.default()
        locations = env.locations
        for dir in locations.config_workspace_base_path().iterdir():
            if dir.is_dir():
                name = dir.name
                if name != marcel.locations.Locations.DEFAULT_WORKSPACE_DIR_NAME:
                    workspace = Workspace(name)
                    if workspace.marker.exists(env):
                        workspace.read_properties(env)  # So that home is known
                        yield workspace

    @staticmethod
    def validate_all(env):
        def check_dir_exists(path, description):
            if not path.exists():
                raise marcel.exception.KillShellException(
                    f'{description} directory missing.')
            if not path.is_dir():
                raise marcel.exception.KillShellException(
                    f'{description} directory is not actually a directory.')

        locations = env.locations
        # Config dir has broken/, workspace/ and nothing else.
        check_dir_exists(locations.config_workspace_base_path(), 'Workspace configuration')
        check_dir_exists(locations.config_broken_workspace_base_path(), 'Broken workspace configuration')
        # Data dir has broken/, workspace/ and nothing else.
        check_dir_exists(locations.data_workspace_base_path(), 'Workspace data')
        check_dir_exists(locations.data_broken_workspace_base_path(), 'Broken workspace data')
        # The data and config workspace directories should have subdirectories with matching names.
        config_workspaces = set(locations.config_workspace_base_path().iterdir())
        data_workspaces = set(locations.data_workspace_base_path().iterdir())
        broken_workspaces = ((config_workspaces - data_workspaces) |
                             (data_workspaces - config_workspaces))
        for workspace in Workspace.list(env):
            workspace_problems = workspace.validate(env)
            for problem in workspace_problems:
                print(problem, file=sys.stderr)
            broken_workspaces.add(workspace.name)

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
        self.marker.unowned(env).touch(mode=0o000, exist_ok=False)
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

    def share_workspace(self, env):
        assert self.is_default()
        # exist_ok = True: We could be returning to the default workspace, previously opened in this process.
        self.marker.owned(env).touch(mode=0o000, exist_ok=True)

    def unshare_workspace(self, env):
        assert self.is_default()
        self.marker.owned(env).unlink(missing_ok=True)

    def lock_workspace(self, env):
        assert not self.is_default()
        owner = self.owner(env)
        if owner is None:
            # Lock the file by renaming it. Check for success, to guard against another process trying to
            # lock the same workspace.
            owned_marker_path = self.marker.owned(env)
            self.marker.unowned(env).rename(owned_marker_path)
            return owned_marker_path.exists()
        elif owner == env.locations.pid:  # locations.pid is the pid of the topmost process
            # Already locked
            return True
        else:
            # Locked by another process
            if marcel.util.process_exists(owner):
                return False
            else:
                # Owner disappeared. Steal the marker file.
                abandoned_marker_path = self.marker.owned(env, owner)
                owned_marker_path = self.marker.owned(env)
                abandoned_marker_path.rename(owned_marker_path)
                # If owned_marker_path doesn't exist, another process was stealing the file at exactly the same time?!
                return owned_marker_path.exists()

    def unlock_workspace(self, env):
        assert not self.is_default()
        owner = self.owner(env)
        if owner is None:
            # Someone is unlocking an unlocked workspace? I'll allow it.
            pass
        elif owner == env.locations.pid:  # locations.pid is the pid of the topmost process
            # Unlock
            unowned_marker_path = self.marker.unowned(env)
            self.marker.owned(env).rename(unowned_marker_path)
            assert unowned_marker_path.exists(), self
        else:
            # Owned by someone else?!
            assert False, self

    def read_properties(self, env):
        assert not self.is_default()
        with open(env.locations.workspace_properties_file_path(self), 'rb') as properties_file:
            unpickler = dill.Unpickler(properties_file)
            self.properties = unpickler.load()
        self.properties.update_open_time()

    def write_properties(self, env):
        assert not self.is_default()
        self.properties.update_save_time()
        with open(env.locations.workspace_properties_file_path(self), 'wb') as properties_file:
            pickler = dill.Pickler(properties_file)
            pickler.dump(self.properties)

    def read_environment(self, env):
        with open(env.locations.workspace_environment_file_path(self), 'rb') as environment_file:
            unpickler = dill.Unpickler(environment_file)
            self.persistent_state = unpickler.load()

    def write_environment(self, env):
        with open(env.locations.workspace_environment_file_path(self), 'wb') as environment_file:
            pickler = dill.Pickler(environment_file)
            pickler.dump(env.persistent_state())

    # Return pid of owning process, or None if unowned.
    def owner(self, env):
        # Should only need this for named workspaces.
        assert not self.is_default()
        if self.marker.unowned(env).exists():
            return None
        # First get rid of any markers from processes that don't exist. Shouldn't happend, but still.
        config_dir_path = env.locations.config_dir_path(self)
        if not config_dir_path.exists():
            return None
        for file in config_dir_path.iterdir():
            if file.name.startswith(Marker.FILENAME_ROOT) and len(file.name) > len(Marker.FILENAME_ROOT):
                if not marcel.util.process_exists(Workspace.marker_filename_pid(file.name)):
                    file.unlink()
        # Now find the marker. Something is very wrong if there is anything other than one.
        marker_filename = None
        for file in env.locations.config_dir_path(self).iterdir():
            if file.name.startswith(Marker.FILENAME_ROOT):
                if marker_filename is None:
                    marker_filename = file.name
                else:
                    assert False, f'Multiple marker files in {env.locations.config_file_path(self)}'
        assert marker_filename is not None
        return Workspace.marker_filename_pid(marker_filename)

    def validate(self, env):
        locations = env.locations
        problems = []
        # Config dir has marker file.
        config_dir_path = locations.config_dir_path(self)
        if not self.marker.exists(env):
            problems.append(f'{self}: {Marker.FILENAME_ROOT} marker file is missing.')
        # Config dir has startup.py.
        if not locations.config_file_path(self).exists():
            problems.append(f'{self}: startup.py file is missing.')
        # Config dir has nothing else.
        if len(list(config_dir_path.iterdir())) > 2:
            problems.append(f'{self}: Extraneous files in config directory.')
        # Data dir has env.pickle file.
        if not locations.workspace_environment_file_path(self).exists():
            problems.append(f'{self}: Environment file is missing.')
        # Data dir has properties.pickle file.
        if not locations.workspace_properties_file_path(self).exists():
            problems.append(f'{self}: Properties file is missing.')
        # Data dir has history files.
        if not locations.history_file_path(self).exists():
            problems.append(f'{self}: History file is missing.')
        # Data dir has reservoirs directory.
        if not locations.reservoir_dir_path(self).exists():
            problems.append(f'{self}: Reservoir directory is missing.')
        if not locations.reservoir_dir_path(self).is_dir():
            problems.append(f'{self}: Reservoir directory is not actually a directory.')
        # Data dir has nothing else.
        if len(list(locations.data_dir_path(self).iterdir())) > 4:
            problems.append(f'{self}: Extraneous files in data directory.')
        return problems

    def mark_broken(self, env, now):
        # TODO: Probably not OK to do the following to an open workspace. The marker file indicates in-use.
        locations = env.locations
        config_source = locations.config_dir_path(self)
        if config_source.exists():
            config_target = locations.broken_config_dir_path(self, now)
            shutil.move(config_source, config_target)
        data_source = locations.data_dir_path(self)
        if data_source.exists():
            data_target = locations.broken_data_dir_path(self, now)
            shutil.move(data_source, data_target)

    def cannot_lock_workspace(self):
        raise marcel.exception.KillCommandException(f'Workspace {self.name} is in use by another process.')

    def does_not_exist(self):
        raise marcel.exception.KillCommandException(f'There is no workspace named {self.name}.')

    @staticmethod
    def marker_filename_pid(marker_filename):
        assert marker_filename.startswith(Marker.FILENAME_ROOT)
        return int(marker_filename[marker_filename.rfind('.') + 1:])


class WorkspaceDefault(Workspace):

    def __init__(self):
        super().__init__('')

    # Workspace

    def is_default(self):
        return True

    def open(self, env):
        self.share_workspace(env)
        self.read_environment(env)

    def close(self, env, restart):
        # Reservoirs
        for var, reservoir in env.reservoirs():
            assert type(reservoir) is marcel.reservoir.Reservoir
            if reservoir.pid() == env.pid():
                reservoir.close()
                if not restart:
                    reservoir.ensure_deleted()
        # Environment (Do this last because env.persistent_state() is destructive.)
        if restart:
            self.write_environment(env)
        else:
            env.locations.workspace_environment_file_path(self).unlink(missing_ok=True)
        self.unshare_workspace(env)

    def set_home(self, env, homedir):
        raise marcel.exception.KillCommandException('Default workspace does not have a home directory.')

    def delete(self, env):
        assert False

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
