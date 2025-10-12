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

import marcel.configscript
import marcel.exception
import marcel.locations
import marcel.nestednamespace
import marcel.object.renderable
import marcel.reservoir
import marcel.util

WORKSPACE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class Marker(object):
    FILENAME_ROOT = '.WORKSPACE'

    def __init__(self, workspace):
        self.workspace = workspace

    def exists(self):
        config_dir = self.workspace.locations.config_ws(self.workspace)
        if config_dir.exists():
            for file in config_dir.iterdir():
                if file.name.startswith(Marker.FILENAME_ROOT):
                    return True
        return False

    def unowned(self):
        return self.workspace.locations.config_ws(self.workspace) / Marker.FILENAME_ROOT

    def owned(self, pid=None):
        if pid is None:
            pid = self.workspace.locations.pid
        return self.workspace.locations.config_ws(self.workspace) / f'{Marker.FILENAME_ROOT}.{pid}'

    def ensure_exists(self):
        self.unowned().touch(mode=0o000, exist_ok=True)


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


class VarHandler(object):
    MISSING_VAR = object()

    def __init__(self):
        self.namespace = None
        # Vars that must not be modified after marcel initialization.
        self.immutable_vars = set()
        # Vars that have changed during execution of a command. Returned from Job execution
        # So that changes can be applied in the main process's namespace.
        self.vars_written = set()
        # Immutability of immutable_vars is enforced during normal operation.
        # Marcel startup/shutdown is permitted to change these vars by turning off
        # enforcement.
        self._enforce_immutability = False

    def hasvar(self, var):
        assert var is not None
        return var in self.namespace

    def getvar(self, var):
        assert var is not None
        try:
            value = self.namespace[var]
        except KeyError:
            value = None
        return value

    def setvar(self, var, value, source=None):
        assert var is not None
        self.check_mutability(var)
        current_value = self.namespace.get(var, None)
        self.vars_written.add(var)
        if type(current_value) is marcel.reservoir.Reservoir and value != current_value:
            current_value.ensure_deleted()
        self.namespace.assign(var, value, source)

    def setvar_import(self, var, module, symbol, value):
        assert var is not None
        self.check_mutability(var)
        self.namespace.assign_import(var, module, symbol, value)

    def delvar(self, var):
        assert var is not None
        self.check_mutability(var)
        if var in self.namespace:
            self.vars_written.discard(var)
            value = self.namespace.pop(var)
            if type(value) is marcel.reservoir.Reservoir:
                value.ensure_deleted()
            return value
        else:
            raise KeyError(var)

    def vars(self):
        return self.namespace

    def persistible_vars(self):
        return dict(self.namespace.scopes[0])

    def add_immutable_vars(self, vars):
        self.immutable_vars.update(vars)

    def add_changed_var(self, var):
        self.vars_written.add(var)

    def changes(self):
        changes = {}
        for var in self.vars_written:
            # Bug 273: A pipeline param could show up in vars_written. When the pipeline is exited,
            # and the scope is popped, the namespace is maintained. But the var would still be in
            # vars_written. If a var is in vars_written but not namespace, I'm assuming this is what happened.
            # Another approach is to maintain vars_written on NestedNamespace.pop_scope. But vars_written
            # isn't a nested structure. This would break if the same variable name were used in different scopes.
            value = self.namespace.get(var, VarHandler.MISSING_VAR)
            if value is not VarHandler.MISSING_VAR:
                changes[var] = value
        return changes

    def clear_changes(self):
        self.vars_written.clear()

    def add_written(self, var):
        self.vars_written.add(var)

    def enforce_immutability(self):
        self._enforce_immutability = True

    def check_mutability(self, var):
        if self._enforce_immutability and var in self.immutable_vars:
            raise marcel.exception.KillCommandException(
                f'{var} was defined by marcel, or in your startup script, '
                f'so it cannot be modified or deleted programmatically. '
                f'Edit the startup script instead.')

    # Returns (var, value), where type(value) is Reservoir.
    def reservoirs(self):
        reservoirs = []
        for var in self.namespace.keys():
            value = self.getvar(var)
            if type(value) is marcel.reservoir.Reservoir:
                reservoirs.append((var, value))
        return reservoirs


class Workspace(marcel.object.renderable.Renderable, VarHandler):
    DEFAULT = None

    def __init__(self, name):
        VarHandler.__init__(self)
        assert name is not None
        self.name = name
        self.config_script = marcel.configscript.ConfigScript(self)
        self.properties = None
        self.locations = marcel.locations.Locations()
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

    def exists(self):
        return self.marker.exists()

    def create(self):
        assert not self.exists()
        initial_config_contents = self.locations.config_ws_startup(Workspace.default()).read_text()
        self.create_on_disk(initial_config_contents)

    def open(self, env, initial_namespace=None):
        if self.exists():
            if self.lock_workspace():  # Always granted for default workspace
                self.read_properties()  # Noop for default workspace
                self.namespace = marcel.nestednamespace.NestedNamespace(env)
                if initial_namespace:
                    initial_namespace.add_to_namespace(self.namespace, env)
                config_dict = self.config_script.run()
                for var, value in config_dict.items():
                    self.namespace.assign_permanent(var, value)
                self.add_immutable_vars(config_dict.keys())
                persistent_state = self.read_environment()
                self.namespace.reconstitute(persistent_state, env)
            else:
                self.cannot_lock_workspace()
        else:
            self.does_not_exist()

    def close(self, env, restart):
        # Relocking is okay, so this is a convenient way to test that the workspace is locked.
        if self.lock_workspace():
            # Properties
            self.write_properties()
            # Reservoirs
            for var, reservoir in self.reservoirs():
                assert type(reservoir) is marcel.reservoir.Reservoir
                reservoir.close()
            # Environment
            self.write_environment(self.persistent_state())
            # Mark this workspace object as closed
            self.properties = None
            # Discard workspace
            self.namespace = None
            # Unlock
            self.unlock_workspace()
        else:
            assert False, self

    def set_home(self, home):
        home = pathlib.Path(home).absolute()
        self.properties.set_home(home)
        self.write_properties()

    def delete(self, env):
        if self.exists():
            if self.lock_workspace():
                locations = self.locations
                # config directory
                owned_marker_path = self.marker.owned()
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

    def persistent_state(self):
        assert len(self.namespace.scopes) == 1, len(self.namespace.scopes)
        return dict(self.namespace.scopes[0])

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
        workspaces = [Workspace.default()]
        for dir in env.locations.config_ws().iterdir():
            if dir.is_dir():
                name = dir.name
                if name != marcel.locations.Locations.DEFAULT_WORKSPACE_DIR_NAME:
                    workspace = Workspace(name)
                    if workspace.marker.exists():
                        workspace.read_properties()  # So that home is known
                        workspaces.append(workspace)
        workspaces.sort(key=lambda ws: ws.name)
        return workspaces

    @staticmethod
    def delete_broken(env):
        def delete_subdirs(dir):
            for subdir in dir.iterdir():
                marcel.util.print_to_stderr(env, f'Deleting broken workspace in {subdir}')
                shutil.rmtree(subdir)
        delete_subdirs(env.locations.config_bws())
        delete_subdirs(env.locations.data_bws())

    # Internal

    def create_on_disk(self, initial_config_contents):
        locations = self.locations
        # config
        config_dir = locations.config_ws(self)
        self.create_dir(config_dir)
        config_file_path = locations.config_ws_startup(self)
        config_file_path.write_text(initial_config_contents)
        config_file_path.chmod(0o600)
        self.marker.ensure_exists()
        # data
        self.create_dir(locations.data_ws(self))
        self.create_dir(locations.data_ws_res(self))
        # Environment: Write empty persistent env state
        self.write_environment({})
        if not self.is_default():
            self.properties = WorkspaceProperties()
            self.write_properties()
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

    def lock_workspace(self):
        assert not self.is_default()
        owner = self.owner()
        if owner is None:
            # Lock the file by renaming it. Check for success, to guard against another process trying to
            # lock the same workspace.
            owned_marker_path = self.marker.owned()
            self.marker.unowned().rename(owned_marker_path)
            return owned_marker_path.exists()
        elif owner == self.locations.pid:
            # Already locked
            return True
        elif owner == self.locations.ppid:
            # Locked by parent. This process must be owned by a job executing on behalf of the parent.
            return True
        else:
            # Locked by another process
            if marcel.util.process_exists(owner):
                return False
            else:
                # Owner disappeared. Steal the marker file.
                abandoned_marker_path = self.marker.owned(owner)
                owned_marker_path = self.marker.owned()
                abandoned_marker_path.rename(owned_marker_path)
                # If owned_marker_path doesn't exist, another process was stealing the file at exactly the same time?!
                return owned_marker_path.exists()

    def unlock_workspace(self):
        assert not self.is_default()
        owner = self.owner()
        if owner is None:
            # Someone is unlocking an unlocked workspace? I'll allow it.
            pass
        elif owner == self.locations.pid:  # locations.pid is the pid of the topmost process
            # Unlock
            unowned_marker_path = self.marker.unowned()
            self.marker.owned().rename(unowned_marker_path)
            assert unowned_marker_path.exists(), self
        else:
            # Owned by someone else?!
            assert False, self

    def read_properties(self):
        with open(self.locations.data_ws_prop(self), 'rb') as properties_file:
            unpickler = dill.Unpickler(properties_file)
            self.properties = unpickler.load()
        self.properties.update_open_time()

    def write_properties(self):
        assert not self.is_default()
        self.properties.update_save_time()
        with open(self.locations.data_ws_prop(self), 'wb') as properties_file:
            pickler = dill.Pickler(properties_file)
            pickler.dump(self.properties)

    def read_environment(self):
            with open(self.locations.data_ws_env(self), 'rb') as environment_file:
                unpickler = dill.Unpickler(environment_file)
                return unpickler.load()

    def write_environment(self, persistent_state):
        assert persistent_state is not None
        with open(self.locations.data_ws_env(self), 'wb') as environment_file:
            pickler = dill.Pickler(environment_file)
            pickler.dump(persistent_state)

    # Return pid of owning process, or None if unowned.
    def owner(self):
        # Should only need this for named workspaces.
        assert not self.is_default()
        if self.marker.unowned().exists():
            return None
        if not self.locations.config_ws(self).exists():
            return None
        # First get rid of any markers from processes that don't exist. Shouldn't happen, but still.
        self.delete_abandoned_markers()
        # Now find the marker. Something is very wrong if there is anything other than one.
        marker_filename = None
        for file in self.locations.config_ws(self).iterdir():
            if file.name.startswith(Marker.FILENAME_ROOT):
                if marker_filename is None:
                    marker_filename = file.name
                else:
                    assert False, f'Multiple marker files in {self.locations.config_ws_startup(self)}'
        assert marker_filename is not None
        return Workspace.marker_filename_pid(marker_filename)

    def validate(self):
        return WorkspaceValidater(self).validate()

    def mark_broken(self, now):
        # TODO: Probably not OK to do the following to an open workspace. The marker file indicates in-use.
        locations = self.locations
        config_source = locations.config_ws(self)
        if config_source.exists():
            config_target = locations.config_bws(self, now)
            shutil.move(config_source, config_target)
        data_source = locations.data_ws(self)
        if data_source.exists():
            data_target = locations.data_bws(self, now)
            shutil.move(data_source, data_target)

    def delete_abandoned_markers(self):
        for file in self.locations.config_ws(self).iterdir():
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

    def exists(self):
        return True

    def read_properties(self):
        pass

    def close(self, env, restart):
        # Reservoirs
        current_pid = self.locations.pid
        for var, reservoir in self.reservoirs():
            assert type(reservoir) is marcel.reservoir.Reservoir
            if reservoir.pid() == current_pid:
                reservoir.close()
                if not restart:
                    reservoir.ensure_deleted()
        if restart:
            self.write_environment(self.persistent_state())
        else:
            self.locations.data_ws_env(self).unlink(missing_ok=True)

    def set_home(self, homedir):
        raise marcel.exception.KillCommandException('Default workspace does not have a home directory.')

    def delete(self, env):
        assert False

    def validate(self):
        return WorkspaceDefaultValidater(self).validate()

    # Internal

    def read_environment(self):
        try:
            persistent_state = super().read_environment()
        except FileNotFoundError:
            # This can happen on startup when the default workspace for this process hasn't been saved yet.
            # Environment.restore_persistent_state_from_workspace defines what keys should be in persistent_state.
            persistent_state = {}
        return persistent_state

    def lock_workspace(self):
        return True


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

    def __init__(self, workspace):
        self.locations = marcel.locations.Locations()
        self.workspace = workspace
        self.errors = []

    def validate(self):
        locations = self.locations
        workspace = self.workspace
        # Don't need to check existence of config dir. The persistence.validate_all loop checks workspaces that
        # exist in this dir.
        # Config dir has marker file.
        config_dir_path = locations.config_ws(workspace)
        # Workspace.owner() gets rid of unowned marker files.
        self.workspace.delete_abandoned_markers()
        if not self.workspace.marker.exists():
            # Could happen if Workspace.owner() deleted the marker, because it was owned by
            # a process that no longer exists. Create a new marker.
            self.workspace.marker.ensure_exists()
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
        locations = self.locations
        workspace = self.workspace
        if not locations.data_ws_env(workspace).exists():
            self.missing(locations.data_ws_env(workspace))

    def validate_properties_file(self):
        locations = self.locations
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
        locations = self.locations
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
