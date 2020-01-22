import pathlib

import osh.error


class Environment:

    def __init__(self):
        self.current_dir = pathlib.Path.cwd()

    def pwd(self):
        return self.current_dir

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = self.current_dir / directory
        try:
            self.current_dir = new_dir.resolve(strict=True)
        except FileNotFoundError:
            raise osh.error.CommandKiller('Cannot cd into %s from %s. Target %s does not exist.' %
                                          (directory, self.current_dir, new_dir))


ENV = Environment()
