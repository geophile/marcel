import pathlib

import marcel.exception


class Locations(object):

    def __init__(self, env):
        self.env = env
        self.home = pathlib.Path.home().expanduser()

    def config_path(self):
        return self._dir('XDG_CONFIG_HOME', '.config') / 'startup.py'

    def history_path(self):
        return self._dir('XDG_DATA_HOME', '.local', 'share') / 'history'

    def _dir(self, xdg_var, *path_from_base):
        base = self.env.getvar(xdg_var)
        if base is None:
            base = self.home
            for dir in path_from_base:
                base = base / dir
        else:
            if type(base) is not str:
                raise marcel.exception.KillShellException(
                    f'Type of {xdg_var} is {type(base)}. If defined, it must be a string.')
            base = pathlib.Path(base).expanduser()
        dir = base / 'marcel'
        if dir.exists():
            if not dir.is_dir():
                raise marcel.exception.KillShellException(f'Not a directory: {dir}')
        else:
            dir.mkdir(exist_ok=False)
        return dir

