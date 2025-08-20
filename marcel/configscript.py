# This file is part of Marcel.
#
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
# option) any later version.
#
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import marcel.env
import marcel.exception
import marcel.locations
import marcel.util

class ConfigScript(object):

    def __init__(self, workspace):
        self.workspace = workspace
        self.locations = marcel.locations.Locations()

    def run(self):
        # Make sure that never mutable vars aren't modified during startup.
        # Read the startup script, getting the var/value pairs defined in the script.
        locals = self.read_config()
        # Find the vars defined during startup
        startup_vars = set(locals.keys())
        # Check that never mutable vars didn't change.
        never_mutable_assigned = [var
                                  for var in marcel.env.Environment.never_mutable()
                                  if var in locals]
        if never_mutable_assigned:
            raise marcel.exception.KillCommandException(
                f'Startup script must not modify the value of variables'
                f' {", ".join(never_mutable_assigned)}.')
        return {var: locals[var] for var in startup_vars}

    def read_config(self):
        config_path = self.locations.config_ws_startup(self.workspace)
        try:
            with open(config_path) as config_file:
                config_source = config_file.read()
        except Exception as e:
            raise marcel.exception.KillCommandException(
                f'Unable to locate or read config script for {self.workspace}: {config_path}')
        # Execute the config file. Imported and newly-defined symbols go into locals, which
        # will then be added to self.namespace, for use in the execution of op functions.
        locals = dict()
        try:
            exec(config_source, self.workspace.namespace, locals)
        except Exception as e:
            marcel.util.print_stack_of_current_exception()
            raise marcel.exception.StartupScriptException(self.workspace, e)
        return locals
