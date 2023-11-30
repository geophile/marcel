#!/usr/bin/env python3

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

import atexit
import getpass
import os
import signal
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
import marcel.opmodule
import marcel.nestednamespace
import marcel.util
import marcel.version

from marcel.api import *

# stdin carries the following from the client process:
#   - The client's python version (checked to match server's, see bug 169.)
#   - The client's environment
#   - The pipelines to be executed
#   - Possibly a kill signal
# The kill signal may be delayed and may never arrive. Pipeline execution takes place
# on a thread so that stdin can be monitored for the kill signal and then acted upon.


TRACE = marcel.util.Trace(f'/tmp/farcel-{os.getuid()}.log')


class PythonVersionMismatch(Exception):

    def __init__(self, client_python_version, server_python_version):
        super().__init__(f'Python version mismatch between client '
                         f'({PythonVersionMismatch.version_string(client_python_version)}) and server '
                         f'({PythonVersionMismatch.version_string(server_python_version)}).')

    @staticmethod
    def version_string(v):
        return f'{v[0]}.{v[1]}'


class PickleOutput(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.pickler = dill.Pickler(sys.stdout.buffer)

    def __repr__(self):
        return 'pickleoutput()'

    def setup(self, env):
        pass

    def receive(self, env, x):
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
        self.pickler = PickleOutput()
        pipeline.append(self.pickler)
        self.pipeline = pipeline

    def run(self):
        try:
            # self.check_python_version()
            TRACE.write(f'PipelineRunner: About to setup {self.pipeline}')
            self.pipeline.set_error_handler(noop_error_handler)
            self.pipeline.setup(self.env)
            TRACE.write(f'PipelineRunner: About to run {self.pipeline}')
            self.pipeline.first_op().run(self.env)
            self.pipeline.flush(self.env)
        except BaseException as e:
            TRACE.write(f'PipelineRunner.run caught {type(e)}: {e}')
            with TRACE.open() as file:
                marcel.util.print_stack_of_current_exception(file)
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
            with TRACE.open() as file:
                marcel.util.print_stack_of_current_exception(file)
    except BaseException as e:
        TRACE.write(f'Caught {type(e)} in kill_self_and_descendents: {e}')
        with TRACE.open() as file:
            marcel.util.print_stack_of_current_exception(file)


def shutdown():
    pass


def noop_error_handler(env, error):
    TRACE.write(f'Pipeline encountered error: {error}')


def main():
    try:
        TRACE.write('-' * 80)
        TRACE.write(getpass.getuser())
        TRACE.write(f'{datetime.datetime.now()}')
        # Use sys.stdin.buffer because we want binary data, not the text version
        input = dill.Unpickler(sys.stdin.buffer)
        # Python version from client
        client_python_version = input.load()
        # Client-side marcel usage, api or script.
        marcel_usage = input.load()
        # pipelines from client
        pipeline = input.load()
        if marcel_usage == 'api':
            env = marcel.env.EnvironmentAPI.create(dict())
        elif marcel_usage == 'script':
            env = marcel.env.EnvironmentScript.create()
        else:
            assert False, marcel_usage
        version = env.getvar('MARCEL_VERSION')
        TRACE.write(f'Marcel version {version}')
        TRACE.write(f'pipeline: {pipeline}')
        atexit.register(shutdown)
        pipeline_runner = PipelineRunner(client_python_version, env, pipeline)
        pipeline_runner.start()
    except Exception as e:
        TRACE.write(f'Caught {type(e)}: {e}')
        with TRACE.open() as file:
            marcel.util.print_stack_of_current_exception(file)
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


main()
