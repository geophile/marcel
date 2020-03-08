import pathlib

import marcel.object.cluster
import marcel.object.colorscheme


class Configuration:
    CONFIG_FILENAME = '.marcel.py'
    DEFAULT_PROMPT = ['$ ']

    def __init__(self, env_vars):
        self.env_vars = env_vars
        self.colors = {}
        self.color_scheme = None
        self.clusters = {}
        self.prompt = Configuration.DEFAULT_PROMPT
        self.continuation_prompt = Configuration.DEFAULT_PROMPT

    def read_config(self, config_path):
        config_path = (pathlib.Path(config_path)
                       if config_path else
                       pathlib.Path.home() / Configuration.CONFIG_FILENAME)
        if config_path.exists():
            with open(config_path.as_posix()) as config_file:
                config_source = config_file.read()
            # globals needs env vars, and the functions handling definitions of colors, colorschemes, clusters.
            globals = dict.copy(self.env_vars)
            globals['define_colors'] = self.define_colors
            globals['define_color_scheme'] = self.define_colorscheme
            globals['define_prompt'] = self.define_prompt
            globals['define_continuation_prompt'] = self.define_continuation_prompt
            globals['define_cluster'] = self.define_cluster
            globals['Color'] = marcel.object.colorscheme.Color
            locals = {}
            exec(config_source, globals, locals)

    def define_colors(self, **kwargs):
        self.colors = kwargs

    def define_colorscheme(self,
                           prompt_shell_indicator=None,
                           prompt_who=None,
                           prompt_dir=None,
                           prompt_separator=None,
                           file_file=None,
                           file_dir=None,
                           file_link=None,
                           file_executable=None,
                           file_extension=None,
                           process_pid=None,
                           process_commandline=None,
                           error=None):
        self.color_scheme = marcel.object.colorscheme.ColorScheme()
        self.color_scheme.prompt_shell_indicator = self.color(prompt_shell_indicator)
        self.color_scheme.prompt_who = self.color(prompt_who)
        self.color_scheme.prompt_dir = self.color(prompt_dir)
        self.color_scheme.prompt_separator = self.color(prompt_separator)
        self.color_scheme.file_file = self.color(file_file)
        self.color_scheme.file_dir = self.color(file_dir)
        self.color_scheme.file_link = self.color(file_link)
        self.color_scheme.file_executable = self.color(file_executable)
        self.color_scheme.file_extension = self.color(file_extension)
        self.color_scheme.process_pid = self.color(process_pid)
        self.color_scheme.process_commandline = self.color(process_commandline)
        self.color_scheme.error = self.color(error)

    def define_prompt(self, prompt):
        self.prompt = prompt

    def define_continuation_prompt(self, prompt):
        self.continuation_prompt = prompt

    def define_cluster(self, name, hosts, user, identity):
        self.clusters[name] = marcel.object.cluster.Cluster(name, hosts, user, identity)

    def color(self, x):
        return (self.colors.get(x, None)
                if isinstance(x, str) else
                x)
