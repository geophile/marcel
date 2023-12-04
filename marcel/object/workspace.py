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
        return format_time(self.create_time)

    def update_open_time(self):
        self.last_open_time = time.time()

    def update_save_time(self):
        self.last_save_time = time.time()


class Workspace(marcel.object.renderable.Renderable):

    # name = None for default workspace
    def __init__(self, env, name=None):
        self.env = env
        self.name = name
        self.properties = None

    def __repr__(self):
        return f'Workspace({self.name if self.name else "DEFAULT"})'

    # ws op support

    def new(self):
        locations = self.env.locations
        # config
        config_dir = locations.config_dir_path(self.name)
        self.create_dir(config_dir)
        shutil.copyfile(locations.config_file_path(), locations.config_file_path(self.name))
        locations.workspace_marker_file_path(self.name).touch(mode=0o600, exist_ok=False)
        # history
        history_dir = locations.data_dir_path(self.name)
        self.create_dir(history_dir)
        locations.history_file_path(self.name).touch(mode=0o000, exist_ok=False)
        self.properties = WorkspaceProperties()
        self.save_workspace()

    def list(self):
        locations = self.env.locations
        for dir in locations.config_dir_path().iterdir():
            if dir.is_dir() and locations.workspace_marker_file_path(dir).exists():
                name = dir.name
                workspace = Workspace(self.env, name)
                with open(locations.workspace_properties_file_path(name), 'rb') as properties_file:
                    pickler = dill.Unpickler(properties_file)
                    workspace.properties = pickler.load()
                    yield workspace

    def close(self):
        if self.properties:  # Will be None for default workspace
            self.properties.update_save_time()
        self.save_workspace()

    @staticmethod
    def default():
        return Workspace(None)

    # Renderable

    def render_compact(self):
        return f'Workspace({self.name})'

    def render_full(self, color_scheme):
        wp = self.properties
        return f'Workspace({self.name}  ' \
               f'created {format_time(wp.create_time)}  ' \
               f'last open {format_time(wp.last_open_time)}  ' \
               f'last save {format_time(wp.last_save_time)})'

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

    def save_workspace(self):
        locations = self.env.locations
        if self.name is not None:
            # Properties
            with open(locations.workspace_properties_file_path(self.name), 'wb') as properties_file:
                pickler = dill.Pickler(properties_file)
                pickler.dump(self.properties)
        # else: Default workspace, properties not needed
        # Environment
        with open(locations.workspace_environment_file_path(self.name), 'wb') as environment_file:
            pickler = dill.Pickler(environment_file)
            pickler.dump(self.env)
        # History saved by main.reader.
