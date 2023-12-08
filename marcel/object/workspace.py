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
        self.last_open_time = self.create_time
        self.last_save_time = self.create_time

    def __repr__(self):
        return (f'WorkspaceProperties('
                f'create = {format_time(self.create_time)}, '
                f'open = {format_time(self.last_open_time)}, '
                f'save = {format_time(self.last_save_time)})')

    def update_open_time(self):
        self.last_open_time = time.time()

    def update_save_time(self):
        self.last_save_time = time.time()


class WorkspaceDefault(marcel.object.renderable.Renderable):

    def __init__(self):
        self.name = None

    def __repr__(self):
        return 'Workspace(DEFAULT)'

    def is_default(self):
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

    def __init__(self, name):
        super().__init__()
        assert name is not None
        self.name = name
        self.properties = None
        self.saved_env = None

    def __repr__(self):
        return f'Workspace({self.name})'

    def is_default(self):
        return False

    def exists(self, env):
        return env.locations.workspace_marker_file_path(self.name).exists()

    def create(self, env):
        locations = env.locations
        # config
        config_dir = locations.config_dir_path(self.name)
        self.create_dir(config_dir)
        shutil.copyfile(locations.config_file_path(None), locations.config_file_path(self.name))
        locations.workspace_marker_file_path(self.name).touch(mode=0o000, exist_ok=False)
        # history
        history_dir = locations.data_dir_path(self.name)
        self.create_dir(history_dir)
        locations.history_file_path(self.name).touch(mode=0o600, exist_ok=False)
        self.properties = WorkspaceProperties()
        self.close(env)

    def open(self, env):
        locations = env.locations
        # Properties
        with open(locations.workspace_properties_file_path(self.name), 'rb') as properties_file:
            unpickler = dill.Unpickler(properties_file)
            self.properties = unpickler.load()
        # Environment
        with open(locations.workspace_environment_file_path(self.name), 'rb') as environment_file:
            unpickler = dill.Unpickler(environment_file)
            self.saved_env = unpickler.load()
        self.properties.update_open_time()

    def close(self, env):
        self.properties.update_save_time()
        locations = env.locations
        with open(locations.workspace_properties_file_path(self.name), 'wb') as properties_file:
            pickler = dill.Pickler(properties_file)
            pickler.dump(self.properties)
        with open(locations.workspace_environment_file_path(self.name), 'wb') as environment_file:
            pickler = dill.Pickler(environment_file)
            pickler.dump(env.persistent_state())

    @staticmethod
    def list(env):
        yield Workspace.DEFAULT
        locations = env.locations
        for dir in locations.config_dir_path(None).iterdir():
            if dir.is_dir() and locations.workspace_marker_file_path(dir).exists():
                name = dir.name
                workspace = Workspace(name)
                with open(locations.workspace_properties_file_path(name), 'rb') as properties_file:
                    pickler = dill.Unpickler(properties_file)
                    workspace.properties = pickler.load()
                    yield workspace

    # Renderable

    def render_compact(self):
        return f'Workspace({self.name})'

    def render_full(self, color_scheme):
        wp = self.properties
        return ('Workspace(DEFAULT)' if wp is None else
                f'Workspace({self.name}  '
                f'created {format_time(wp.create_time)}  '
                f'last open {format_time(wp.last_open_time)}  '
                f'last save {format_time(wp.last_save_time)})')

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
