# This file is part of Marcel.
#
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
#
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

#!/usr/bin/python3

import atexit
import getpass
import os
import pathlib
import signal
import socket
import sys
import threading

import dill
import psutil

import marcel.core
import marcel.env
import marcel.exception
import marcel.locations
import marcel.object.color
import marcel.object.error
import marcel.nestednamespace
import marcel.util
import marcel.version

# stdin carries the following from the client process:
#   - The client's python version (checked to match server's, see bug 169.)
#   - The client's environment
#   - The pipeline to be executed
#   - Possibly a kill signal
# The kill signal may be delayed and may never arrive. Pipeline execution takes place
# on a thread so that stdin can be monitored for the kill signal and then acted upon.


TRACE = marcel.util.Trace('/tmp/farcel.log', enabled=True)


class PythonVersionMismatch(Exception):

    def __init__(self, client_python_version, server_python_version):
        super().__init__(f'Python version mismatch between client ('
                         f'{PythonVersionMismatch.version_string(client_python_version)} and server '
                         f'{PythonVersionMismatch.version_string(server_python_version)}.')

    @staticmethod
    def version_string(v):
        return f'{v[0]}.{v[1]}'


class PickleOutput(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.pickler = dill.Pickler(sys.stdout.buffer)

    def __repr__(self):
        return 'pickleoutput()'

    def setup(self):
        pass

    def receive(self, x):
        TRACE.write(f'Pickling: ({type(x)}) {x}')
        self.pickler.dump(x)

    def cleanup(self):
        TRACE.write('Closing stdout')
        sys.stdout.buffer.close()

    def receive_error(self, error):
        TRACE.write(f'Pickling error: ({type(error)}) {error}')
        self.pickler.dump(error)
        super().receive_error(error)


class PipelineRunner(threading.Thread):

    def __init__(self, client_python_version, env, pipeline):
        super().__init__()
        self.client_python_version = client_python_version
        self.env = env
        self.pickler = PickleOutput(env)
        pipeline.append(self.pickler)
        self.pipeline = pipeline

    def run(self):
        try:
            self.check_python_version()
            TRACE.write(f'PipelineRunner: About to setup {self.pipeline}')
            self.pipeline.setup()
            TRACE.write(f'PipelineRunner: About to run {self.pipeline}')
            self.pipeline.first_op().run()
            self.pipeline.flush()
        except BaseException as e:
            TRACE.write(f'PipelineRunner.run caught {type(e)}: {e}')
            marcel.util.print_stack(file=TRACE.file)
            self.pickler.receive_error(marcel.object.error.Error(e))
        TRACE.write('PipelineRunner: Execution complete.')

    def check_python_version(self):
        server_python_version = sys.version_info.major, sys.version_info.minor
        if server_python_version != self.client_python_version:
            raise PythonVersionMismatch(self.client_python_version, server_python_version)


def kill_descendents(signal_id):
    TRACE.write('In kill_self_and_descendents')
    try:
        pid = os.getpid()
        try:
            process = psutil.Process(pid)
            for p in process.children(recursive=True):
                TRACE.write(f'Killing descendent pid {p.pid}')
                p.send_signal(signal_id)
            # # Suicide
            # TRACE.write(f'Killing self, pid = {pid}')
            # process.kill(signal_id)
        except Exception as e:
            TRACE.write(f'Caught exception while killing process {pid} and descendents: {e}')
            marcel.util.print_stack(TRACE.file)
    except BaseException as e:
        TRACE.write(f'Caught {type(e)} in kill_self_and_descendents: {e}')
        marcel.util.print_stack(TRACE.file)


# Adapted from Environment.read_config
def read_config(config_path=None):
    current_dir = pathlib.Path.cwd().resolve()
    namespace = {
        'USER': getpass.getuser(),
        'HOME': pathlib.Path.home().resolve().as_posix(),
        'HOST': socket.gethostname(),
        'MARCEL_VERSION': marcel.version.VERSION,
        'PWD': current_dir.as_posix(),
        'DIRS': [current_dir.as_posix()],
        'BOLD': marcel.object.color.Color.BOLD,
        'ITALIC': marcel.object.color.Color.ITALIC,
        'COLOR_SCHEME': marcel.object.color.ColorScheme(),
        'Color': marcel.object.color.Color,
    }
    locations = marcel.locations.Locations(marcel.env.Environment())
    config_path = locations.config_path()
    if config_path.exists():
        with open(config_path.as_posix()) as config_file:
            config_source = config_file.read()
        locals = {}
        # Execute the config file. Imported and newly-defined symbols go into locals, which
        # will then be added to self.namespace, for use in the execution of op functions.
        exec(config_source, namespace, locals)
        namespace.update(locals)
    return namespace


def shutdown():
    pass


def main():
    def noop_error_handler(env, error):
        pass

    try:
        namespace = marcel.nestednamespace.NestedNamespace(read_config())
        # Use sys.stdin.buffer because we want binary data, not the text version
        input = dill.Unpickler(sys.stdin.buffer)
        # Python version from client
        client_python_version = input.load()
        # env from client
        env = input.load()
        namespace.update(env.namespace)
        env.namespace = namespace
        env.main_pid = os.getpid()
        # pipeline from client
        pipeline = input.load()
        version = env.getvar('MARCEL_VERSION')
        TRACE.write(f'Marcel version {version}')
        TRACE.write(f'pipeline: {pipeline}')
        atexit.register(shutdown)
        pipeline.set_env(env)
        pipeline.set_error_handler(noop_error_handler)
        pipeline_runner = PipelineRunner(client_python_version, env, pipeline)
        pipeline_runner.start()
    except Exception as e:
        TRACE.write(f'Caught {type(e)}: {e}')
        marcel.util.print_stack(TRACE.file)
    try:
        signal_id = input.load()
        TRACE.write(f'Received signal {signal_id}')
        kill_descendents(signal_id)
    except EOFError:
        TRACE.write('Received EOF')
        while pipeline_runner.is_alive():
            TRACE.write(f'PipelineRunner alive: {pipeline_runner.is_alive()}')
            pipeline_runner.join(0.1)
        TRACE.write(f'PipelineRunner alive: {pipeline_runner.is_alive()}')
        kill_descendents(signal.SIGTERM)
    finally:
        TRACE.write('Exiting')
        TRACE.close()


main()
