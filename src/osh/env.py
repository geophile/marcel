import getpass
import os
import socket

import osh.error
import osh.object.cluster
from osh.util import *

ENV = None
DEFAULT_PROMPT = ['$ ']


class Environment:
    CONFIG_PATH_NAME = '.osh2rc'

    @staticmethod
    def initialize(config_file):
        global ENV
        ENV = Environment(config_file)

    def __init__(self, config_file):
        self._user = getpass.getuser()
        self._homedir = pathlib.Path.home()
        self._current_dir = pathlib.Path.cwd()
        self._host = socket.gethostname()
        self._globals = {
            'USER': self._user,
            'HOME': self._homedir.as_posix(),
            'HOST': self._host,
            'PWD': self._current_dir.as_posix()
        }
        self._color_scheme = None
        self.read_config(config_file)  # Sets _globals
        self._color_scheme = self._globals.get('COLOR_SCHEME', None)
        if not isinstance(self._color_scheme, osh.object.colorscheme.ColorScheme):
            if self._color_scheme is not None:
                print('Invalid COLOR_SCHEME specified, using defafult', file=sys.stderr)
            self._color_schema = osh.object.colorscheme.ColorScheme()

    def prompt(self):
        prompt_list = self._globals.get('PROMPT', DEFAULT_PROMPT)
        buffer = []
        color = None
        for x in prompt_list:
            if isinstance(x, osh.object.colorscheme.Color):
                color = x
            else:
                if callable(x):
                    x = x()
                if color is not None:
                    x = colorize(x, color)
                buffer.append(x)
        return ''.join(buffer)

    def pwd(self):
        return self._current_dir

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = self._current_dir / directory
        try:
            self._current_dir = new_dir.resolve(strict=True)
            self._globals['PWD'] = self._current_dir.as_posix()
            # So that executables have the same view of the current directory.
            os.chdir(self._current_dir)
        except FileNotFoundError:
            raise osh.error.KillCommandException('Cannot cd into %s from %s. Target %s does not exist.' %
                                                 (directory, self._current_dir, new_dir))

    def globals(self):
        return self._globals

    def cluster(self, name):
        symbol = self._globals.get(name, None)
        return symbol if symbol and type(symbol) is osh.object.cluster.Cluster else None

    def color_scheme(self):
        assert isinstance(self._color_scheme, osh.object.colorscheme.ColorScheme), self._color_scheme
        return self._color_scheme

    def read_config(self, requested_config_path):
        config_path = (pathlib.Path(requested_config_path)
                       if requested_config_path else
                       pathlib.Path.home() / Environment.CONFIG_PATH_NAME)
        if config_path.exists():
            with open(config_path.as_posix()) as config_file:
                config_source = config_file.read()
                exec(config_source, self._globals)

