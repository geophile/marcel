import getpass
import os
import pathlib
import socket

import marcel.config
import marcel.exception
import marcel.object.cluster
import marcel.object.colorscheme
import marcel.object.colorscheme
from marcel.util import *


class Environment:

    def __init__(self, config_file):
        self._user = getpass.getuser()
        self._homedir = pathlib.Path.home().resolve()
        self._host = socket.gethostname()
        try:
            current_dir = pathlib.Path.cwd().resolve()
        except FileNotFoundError:
            raise marcel.exception.KillShellException(
                'Current directory does not exist! cd somewhere else and try again.')
        self._dir_stack = [current_dir]
        self._vars = {  # Environment variables
            'USER': self._user,
            'HOME': self._homedir.as_posix(),
            'HOST': self._host,
            'PWD': self.pwd().as_posix()
        }
        self._config = marcel.config.Configuration(self._vars)
        self._config.read_config(config_file)
        self._colors = self._config.colors
        self._color_scheme = self._config.color_scheme

    def __getstate__(self):
        assert False

    def __setstate__(self, state):
        assert False

    def prompts(self):
        return (self._prompt_string(self._config.prompt),
                self._prompt_string(self._config.continuation_prompt))

    def pwd(self):
        return self._dir_stack[-1]

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = (self.pwd() / directory.expanduser()).resolve(False)  # False: due to bug 27
        try:
            if not new_dir.exists():
                raise marcel.exception.KillCommandException(f'Cannot cd into {new_dir}. Directory does not exist.')
            self._dir_stack[-1] = new_dir
            self.setenv('PWD', self.pwd().as_posix())
            # So that executables have the same view of the current directory.
            os.chdir(self.pwd())
        except FileNotFoundError:
            # Fix for bug 27
            pass

    def pushd(self, directory):
        if directory is None:
            if len(self._dir_stack) > 1:
                self._dir_stack[-2:] = [self._dir_stack[-1], self._dir_stack[-2]]
        else:
            assert isinstance(directory, pathlib.Path)
            directory = directory.resolve()
            self._dir_stack.append(directory)
        self.cd(self._dir_stack[-1])

    def popd(self):
        if len(self._dir_stack) > 1:
            self._dir_stack.pop()
            self.cd(self._dir_stack[-1])

    def reset_dir_stack(self):
        self._dir_stack = [self._dir_stack[-1]]

    def dirs(self):
        dirs = list(self._dir_stack)
        dirs.reverse()
        return dirs

    def cluster(self, name):
        return self.config().clusters.get(name, None)

    def config(self):
        return self._config

    def color_scheme(self):
        return self._color_scheme

    def getenv(self, var):
        return self._vars.get(var, None)

    def setenv(self, var, value):
        self._vars[var] = value
        self._config.set_var_in_function_namespace(var, value)

    def _prompt_string(self, prompt_pieces):
        buffer = []
        color = None
        for x in prompt_pieces:
            # In each iteration, we either have a color, or a prompt component. In the latter case,
            # append it to the buffer, colorizing if color is defined.
            if isinstance(x, marcel.object.colorscheme.Color):
                color = x
                x = None
            elif isinstance(x, str):
                c = self._colors.get(x, None)
                if c:
                    color = c
                    x = None
            elif callable(x):
                # Set up the namespace for calling the function
                x.__globals__.update(self._config.function_namespace)
                x = x()
            else:
                raise marcel.exception.KillShellException(f'Invalid prompt component: {x}')
            if x:
                x = str(x)
                buffer.append(colorize(x, color) if color else x)
        return ''.join(buffer)
