import pathlib

import marcel.object.cluster
import marcel.object.colorscheme


VERSION = '0.3'


class Configuration:
    CONFIG_FILENAME = '.marcel.py'
    DEFAULT_PROMPT = ['$ ']

    def __init__(self, env_vars):
        self.env_vars = env_vars
        self.clusters = {}
        self.prompt = Configuration.DEFAULT_PROMPT
        self.continuation_prompt = Configuration.DEFAULT_PROMPT
        self.function_namespace = None

    def __getstate__(self):
        assert False

    def __setstate__(self, state):
        assert False

    def read_config(self, config_path):
        config_path = (pathlib.Path(config_path)
                       if config_path else
                       pathlib.Path.home() / Configuration.CONFIG_FILENAME)
        if config_path.exists():
            with open(config_path.as_posix()) as config_file:
                config_source = config_file.read()
            # globals needs env vars, and the functions handling definitions of colors, colorschemes, clusters.
            color_scheme = marcel.object.colorscheme.ColorScheme()
            globals = dict.copy(self.env_vars)
            globals['Color'] = marcel.object.colorscheme.Color
            globals['COLOR_SCHEME'] = color_scheme
            globals['define_prompt'] = self.define_prompt
            globals['define_continuation_prompt'] = self.define_continuation_prompt
            globals['define_cluster'] = self.define_cluster
            locals = {}
            exec(config_source, globals, locals)
            # Prepare environment for function evaluation:
            # - locals has symbols defined by, and imported by, config file.
            # - env vars
            self.function_namespace = locals
            self.function_namespace.update(self.env_vars)
            self.function_namespace['COLOR_SCHEME'] = color_scheme

    def define_prompt(self, prompt):
        self.prompt = prompt

    def define_continuation_prompt(self, prompt):
        self.continuation_prompt = prompt

    def define_cluster(self, name, hosts, user, identity):
        self.clusters[name] = marcel.object.cluster.Cluster(name, hosts, user, identity)

    def get_var_in_function_namespace(self, var):
        return self.function_namespace.get(var, None)

    def set_var_in_function_namespace(self, var, value):
        self.function_namespace[var] = value
