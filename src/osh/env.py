import getpass
import socket

import osh.error
import osh.object.cluster
from osh.util import *

ENV = None
SHELL_ID = 'M'


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
        self._hostname = socket.gethostname()
        self._globals = {}
        self._color_scheme = None
        self.read_config(config_file)  # Sets _globals
        self._color_scheme = self._globals.get('COLOR_SCHEME', None)
        if not isinstance(self._color_scheme, osh.object.colorscheme.ColorScheme):
            if self._color_scheme is not None:
                print('Invalid COLOR_SCHEME specified, using defafult', file=sys.stderr)
            self._color_schema = osh.object.colorscheme.ColorScheme()

    def prompt(self):
        color_scheme = self.color_scheme()
        prefix = colorize(str(SHELL_ID) + ' ', color_scheme.prompt_shell_indicator)
        user_host = colorize('%s@%s' % (self._user, self._hostname), color_scheme.prompt_who)
        if self._current_dir == self._homedir:
            dir = '~'
        elif self._current_dir.as_posix().startswith(self._homedir.as_posix()):
            dir = '~' + self._current_dir.as_posix()[len(self._homedir.as_posix()):]
        else:
            dir = self._current_dir.as_posix()
        dir = colorize(dir, color_scheme.prompt_dir)
        return '%s%s%s$ ' % (prefix, user_host, dir)

    def pwd(self):
        return self._current_dir

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = self._current_dir / directory
        try:
            self._current_dir = new_dir.resolve(strict=True)
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

