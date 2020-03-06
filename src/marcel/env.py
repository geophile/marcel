import getpass
import os
import pathlib
import socket
import sys

import marcel.exception
import marcel.object.cluster
import marcel.object.colorscheme
import marcel.object.colorscheme
from marcel.util import *

DEFAULT_PROMPT = ['$ ']


class Environment:
    CONFIG_PATH_NAME = '.marcel.py'

    def __init__(self, config_file):
        self._user = getpass.getuser()
        self._homedir = pathlib.Path.home().resolve()
        self._current_dir = pathlib.Path.cwd().resolve()
        self._host = socket.gethostname()
        self._vars = {  # Environment variables
            'USER': self._user,
            'HOME': self._homedir.as_posix(),
            'HOST': self._host,
            'PWD': self._current_dir.as_posix()
        }
        self._color_scheme = None
        self.read_config(config_file)  # Sets _globals
        self._color_scheme = self._vars.get('COLOR_SCHEME', None)
        if not isinstance(self._color_scheme, marcel.object.colorscheme.ColorScheme):
            if self._color_scheme is not None:
                print('Invalid COLOR_SCHEME specified, using default', file=sys.stderr)
            self._color_schema = marcel.object.colorscheme.ColorScheme()

    def prompts(self):
        return (self._prompt_string(self._vars.get('PROMPT', DEFAULT_PROMPT)),
                self._prompt_string(self._vars.get('CONTINUATION_PROMPT', DEFAULT_PROMPT)))

    def pwd(self):
        return self._current_dir

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = self._current_dir / directory
        try:
            self._current_dir = new_dir.resolve(strict=True)
            self._vars['PWD'] = self._current_dir.as_posix()
            # So that executables have the same view of the current directory.
            os.chdir(self._current_dir)
        except FileNotFoundError:
            raise marcel.exception.KillCommandException(
                'Cannot cd into {} from {}. Directory does not exist.'.format(directory, self._current_dir))

    def globals(self):
        return self._vars

    def cluster(self, name):
        symbol = self._vars.get(name, None)
        return symbol if symbol and type(symbol) is marcel.object.cluster.Cluster else None

    def color_scheme(self):
        assert isinstance(self._color_scheme, marcel.object.colorscheme.ColorScheme), self._color_scheme
        return self._color_scheme

    def read_config(self, requested_config_path):
        config_path = (pathlib.Path(requested_config_path)
                       if requested_config_path else
                       pathlib.Path.home() / Environment.CONFIG_PATH_NAME)
        if config_path.exists():
            with open(config_path.as_posix()) as config_file:
                config_source = config_file.read()
                exec(config_source, self._vars)

    def getenv(self, var):
        return self._vars.get(var, None)

    @staticmethod
    def _prompt_string(prompt_pieces):
        buffer = []
        color = None
        position = 0
        for x in prompt_pieces:
            if isinstance(x, marcel.object.colorscheme.Color):
                color = x
            else:
                if callable(x):
                    x = x()
                    position += len(x)
                else:
                    position += len(str(x))
                if color is not None:
                    x = colorize(x, color)
                buffer.append(x)
        return ''.join(buffer)
