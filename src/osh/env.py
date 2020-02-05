import pathlib

import osh.error


ENV = None


class Environment:

    CONFIG_PATH_NAME = '.osh2rc'
    DEFAULT_PROMPT = '> '

    @staticmethod
    def initialize(config_file):
        global ENV
        ENV = Environment(config_file)

    def __init__(self, config_file):
        self._globals = {}
        self.read_config(config_file)
        self._current_dir = pathlib.Path.cwd()
        self._prompt = Environment.DEFAULT_PROMPT

    def prompt(self):
        return self._prompt

    def pwd(self):
        return self._current_dir

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = self._current_dir / directory
        try:
            self._current_dir = new_dir.resolve(strict=True)
        except FileNotFoundError:
            raise osh.error.CommandKiller('Cannot cd into %s from %s. Target %s does not exist.' %
                                          (directory, self._current_dir, new_dir))

    def globals(self):
        return self._globals

    def read_config(self, requested_config_path):
        config_path = (pathlib.Path(requested_config_path)
                       if requested_config_path else
                       pathlib.Path.home() / Environment.CONFIG_PATH_NAME)
        if config_path.exists():
            with open(config_path.as_posix()) as config_file:
                config_source = config_file.read()
                exec(config_source, self._globals)
