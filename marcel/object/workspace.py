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
import pathlib
import time

import dill
import psutil

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
        config_dir = locations.config_ws(self.workspace)
        if config_dir.exists():
            for file in config_dir.iterdir():
                if file.name.startswith(Marker.FILENAME_ROOT):
                    return True
        return False

    def unowned(self, env):
        return env.locations.config_ws(self.workspace) / Marker.FILENAME_ROOT

    def owned(self, env, pid=None):
        if pid is None:
            pid = env.locations.pid
        return env.locations.config_ws(self.workspace) / f'{Marker.FILENAME_ROOT}.{pid}'

    def ensure_exists(self, env):
        self.unowned(env).touch(mode=0o000, exist_ok=True)


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
            buffer.append(f'home = {self.home}, ')
        buffer.append(f'create = {WorkspaceProperties.format_time(self.create_time)}, ')
        buffer.append(f'open = {WorkspaceProperties.format_time(self.open_time)}, ')
        buffer.append(f'save = {WorkspaceProperties.format_time(self.save_time)})')
        return ''.join(buffer)

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
        initial_config_contents = locations.config_ws_startup(Workspace.default()).read_text()
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
            # Environment (Do this last because env.persistent_state(), (called by
            # write_environment) is destructive.)
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
                owned_marker_path = self.marker.owned(env)
                assert owned_marker_path is not None, self
                owned_marker_path.unlink(missing_ok=False)
                # Use missing_ok=True to enable deletion of damaged workspaces, missing files.
                locations.config_ws_startup(self).unlink(missing_ok=True)
                locations.config_ws(self).rmdir()
                # data directory
                locations.data_ws_hist(self).unlink(missing_ok=True)
                locations.data_ws_prop(self).unlink(missing_ok=True)
                locations.data_ws_env(self).unlink(missing_ok=True)
                reservoir_dir = locations.data_ws_res(self)
                for reservoir_file in reservoir_dir.iterdir():
                    reservoir_file.unlink()
                reservoir_dir.rmdir()
                locations.data_ws(self).rmdir()
            else:
                self.cannot_lock_workspace()
        else:
            self.does_not_exist()

    def home(self):
        # Older workspaces won't have a home property
        return None if self.is_default() or not hasattr(self.properties, 'home') else self.properties.home

    @staticmethod
    def named(name=None):
        return Workspace.default() if name is None else Workspace(name)

    @staticmethod
    def default():
        if Workspace.DEFAULT is None:
            Workspace.DEFAULT = WorkspaceDefault()
        return Workspace.DEFAULT

    @staticmethod
    def list(env):
        yield Workspace.default()
        locations = env.locations
        for dir in locations.config_ws().iterdir():
            if dir.is_dir():
                name = dir.name
                if name != marcel.locations.Locations.DEFAULT_WORKSPACE_DIR_NAME:
                    workspace = Workspace(name)
                    if workspace.marker.exists(env):
                        workspace.read_properties(env)  # So that home is known
                        yield workspace

    @staticmethod
    def delete_broken(env):
        def delete_subdirs(dir):
            for subdir in dir.iterdir():
                marcel.util.print_to_stderr(env, f'Deleting broken workspace in {subdir}')
                shutil.rmtree(subdir)
        delete_subdirs(env.locations.config_bws())
        delete_subdirs(env.locations.data_bws())

    # Internal

    def create_on_disk(self, env, initial_config_contents):
        locations = env.locations
        # config
        config_dir = locations.config_ws(self)
        self.create_dir(config_dir)
        config_file_path = locations.config_ws_startup(self)
        config_file_path.write_text(initial_config_contents)
        config_file_path.chmod(0o600)
        self.marker.ensure_exists(env)
        # data
        self.create_dir(locations.data_ws(self))
        self.create_dir(locations.data_ws_res(self))
        # Environment (Do this last because env.persistent_state(), (called by
        # write_environment) is destructive.)
        self.write_environment(env)
        if not self.is_default():
            self.properties = WorkspaceProperties()
            self.write_properties(env)
        locations.data_ws_hist(self).touch(mode=0o600, exist_ok=True)

    def create_dir(self, dir):
        try:
            dir.mkdir(parents=True)
            assert dir.exists(), dir
        except FileExistsError:
            pass
        except FileNotFoundError:
            raise marcel.exception.KillCommandException(
                f'Workspace name must be usable as a legal filename: {self.name}')

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
        with open(env.locations.data_ws_prop(self), 'rb') as properties_file:
            unpickler = dill.Unpickler(properties_file)
            self.properties = unpickler.load()
        self.properties.update_open_time()

    def write_properties(self, env):
        assert not self.is_default()
        self.properties.update_save_time()
        with open(env.locations.data_ws_prop(self), 'wb') as properties_file:
            pickler = dill.Pickler(properties_file)
            pickler.dump(self.properties)

    def read_environment(self, env):
        with open(env.locations.data_ws_env(self), 'rb') as environment_file:
            unpickler = dill.Unpickler(environment_file)
            self.persistent_state = unpickler.load()

    def write_environment(self, env):
        with open(env.locations.data_ws_env(self), 'wb') as environment_file:
            pickler = dill.Pickler(environment_file)
            pickler.dump(env.persistent_state())

    # Return pid of owning process, or None if unowned.
    def owner(self, env):
        # Should only need this for named workspaces.
        assert not self.is_default()
        if self.marker.unowned(env).exists():
            return None
        if not env.locations.config_ws(self).exists():
            return None
        # First get rid of any markers from processes that don't exist. Shouldn't happen, but still.
        self.delete_abandoned_markers(env)
        # Now find the marker. Something is very wrong if there is anything other than one.
        marker_filename = None
        for file in env.locations.config_ws(self).iterdir():
            if file.name.startswith(Marker.FILENAME_ROOT):
                if marker_filename is None:
                    marker_filename = file.name
                else:
                    assert False, f'Multiple marker files in {env.locations.config_ws_startup(self)}'
        assert marker_filename is not None
        return Workspace.marker_filename_pid(marker_filename)

    def validate(self, env):
        return WorkspaceValidater(env, self).validate()

    def mark_broken(self, env, now):
        # TODO: Probably not OK to do the following to an open workspace. The marker file indicates in-use.
        locations = env.locations
        config_source = locations.config_ws(self)
        if config_source.exists():
            config_target = locations.config_bws(self, now)
            shutil.move(config_source, config_target)
        data_source = locations.data_ws(self)
        if data_source.exists():
            data_target = locations.data_bws(self, now)
            shutil.move(data_source, data_target)

    def delete_abandoned_markers(self, env):
        for file in env.locations.config_ws(self).iterdir():
            if file.name.startswith(Marker.FILENAME_ROOT) and len(file.name) > len(Marker.FILENAME_ROOT):
                pid = Workspace.marker_filename_pid(file.name)
                if not marcel.util.process_exists(pid):
                    file.unlink()

    def cannot_lock_workspace(self):
        raise marcel.exception.KillCommandException(f'Workspace {self.name} is in use by another process.')

    def does_not_exist(self):
        if self.is_default():
            raise marcel.exception.KillShellException('The default workspace is missing?! This should not happen.')
        else:
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
        self.read_environment(env)

    def close(self, env, restart):
        # Reservoirs
        for var, reservoir in env.reservoirs():
            assert type(reservoir) is marcel.reservoir.Reservoir
            if reservoir.pid() == env.pid():
                reservoir.close()
                if not restart:
                    reservoir.ensure_deleted()
        if restart:
            self.write_environment(env)
        else:
            env.locations.data_ws_env(self).unlink(missing_ok=True)

    def set_home(self, env, homedir):
        raise marcel.exception.KillCommandException('Default workspace does not have a home directory.')

    def delete(self, env):
        assert False

    def validate(self, env):
        return WorkspaceDefaultValidater(env, self).validate()

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


class WorkspaceValidater(object):
    class Error(object):

        def __init__(self, workspace_name, message):
            assert isinstance(workspace_name, str)
            assert isinstance(message, str)
            self.workspace_name = workspace_name
            self.message = message

        def __repr__(self):
            name = '<default workspace>' if self.workspace_name == '' else self.workspace_name
            return f'{name}: {self.message}'

    def __init__(self, env, workspace):
        self.env = env
        self.workspace = workspace
        self.errors = []

    def validate(self):
        locations = self.env.locations
        workspace = self.workspace
        # Don't need to check existence of config dir. The persistence.validate_all loop checks workspaces that
        # exist in this dir.
        # Config dir has marker file.
        config_dir_path = locations.config_ws(workspace)
        # Workspace.owner() gets rid of unowned marker files.
        self.workspace.delete_abandoned_markers(self.env)
        if not self.workspace.marker.exists(self.env):
            # Could happen if Workspace.owner() deleted the marker, because it was owned by
            # a process that no longer exists. Create a new marker.
            self.workspace.marker.ensure_exists(self.env)
        # Config dir has startup.py.
        if not locations.config_ws_startup(workspace).exists():
            self.missing(locations.config_ws_startup(workspace))
        # Config dir has nothing else.
        if len(list(config_dir_path.iterdir())) > 2:
            self.extraneous(config_dir_path)
        # Data dir exists
        if not locations.data_ws(workspace).exists():
            self.missing(locations.data_ws(workspace))
        else:
            # env.pickle
            self.validate_env_file()
            # properties.pickle
            self.validate_properties_file()
            # history
            if not locations.data_ws_hist(workspace).exists():
                self.missing(locations.data_ws_hist(workspace))
            # reservoirs
            if not locations.data_ws_res(workspace).exists():
                self.missing(locations.data_ws_res(workspace))
            elif not locations.data_ws_res(workspace).is_dir():
                self.not_a_directory(locations.data_ws_res(workspace))
            # Data dir has nothing else.
            for file in locations.data_ws(workspace).iterdir():
                if not (file.name == 'properties.pickle' or
                        file.name.endswith('env.pickle') or
                        file.name == 'history' or
                        file.name == 'reservoirs'):
                    self.extraneous(locations.data_ws(workspace))
        return self.errors

    def validate_env_file(self):
        locations = self.env.locations
        workspace = self.workspace
        if not locations.data_ws_env(workspace).exists():
            self.missing(locations.data_ws_env(workspace))

    def validate_properties_file(self):
        locations = self.env.locations
        workspace = self.workspace
        if not workspace.is_default() and not locations.data_ws_prop(workspace).exists():
            self.missing(locations.data_ws_prop(workspace))

    def missing(self, path):
        self.errors.append(WorkspaceValidater.Error(self.workspace.name, f'{path} is missing'))

    def extraneous(self, path):
        self.errors.append(WorkspaceValidater.Error(self.workspace.name, f'{path} has extraneous files'))

    def not_a_directory(self, path):
        self.errors.append(WorkspaceValidater.Error(self.workspace.name, f'{path} is not actually a directory'))


class WorkspaceDefaultValidater(WorkspaceValidater):

    def validate(self):
        def delete_abandoned(dir, suffix):
            for file in dir.iterdir():
                if file.name.endswith(suffix):
                    dot = file.name.find('.')
                    try:
                        file_pid = int(file.name[:dot])
                        if file_pid not in pids:
                            file.unlink()
                    except ValueError:
                        self.errors.append(
                            WorkspaceValidater.Error(self.workspace.name,
                                                     f'Unexpected workspace filename in {dir}: {file}'))

        # Delete abandoned files: associated with processes no longer running.
        locations = self.env.locations
        workspace = self.workspace
        pids = set(psutil.pids())
        delete_abandoned(locations.data_ws(workspace), '.env.pickle')
        delete_abandoned(locations.data_ws_res(workspace), '.pickle')
        return super().validate()

    def validate_env_file(self):
        # env.pickle files for default workspaces are transient. They only exist while the process is running,
        # and abandoned files have already been cleaned up.
        pass

    def validate_properties_file(self):
        pass  # Default workspace doesn't have a properties file
