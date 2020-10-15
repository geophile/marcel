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

import marcel.core
import marcel.env
import marcel.exception
import marcel.object.color
import marcel.object.error
import marcel.object.process
import marcel.nestednamespace
import marcel.util
import marcel.version

# stdin carries the following from the client process:
#   - The client's environment
#   - The pipeline to be executed
#   - Possibly a kill signal
# The kill signal may be delayed and may never arrive. Pipeline execution takes place
# on a thread so that stdin can be monitored for the kill signal and then acted upon.


CONFIG_FILENAME = '.marcel.py'
TRACE = marcel.util.Trace('/tmp/farcel.log')


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

    def receive_error(self, error):
        TRACE.write(f'Pickling error: ({type(error)}) {error}')
        self.pickler.dump(error)
        super().receive_error(error)

    def receive_complete(self):
        TRACE.write('Closing stdout')
        sys.stdout.buffer.close()


class PipelineRunner(threading.Thread):

    def __init__(self, env, pipeline):
        super().__init__()
        self.env = env
        self.pickler = PickleOutput(env)
        pipeline.append(self.pickler)
        self.pipeline = pipeline

    def run(self):
        try:
            TRACE.write(f'PipelineRunner: About to setup {self.pipeline}')
            self.pipeline.setup()
            TRACE.write(f'PipelineRunner: About to run {self.pipeline}')
            self.pipeline.first_op().receive_input(None)
        # except marcel.exception.KillCommandException as e:
        #     self.pickler.receive_error(marcel.object.error.Error(e))
        except BaseException as e:
            TRACE.write(f'PipelineRunner.run caught {type(e)}: {e}')
            marcel.util.print_stack(file=TRACE.file)
            self.pickler.receive_error(marcel.object.error.Error(e))
        self.pipeline.receive_complete()
        TRACE.write('PipelineRunner: Execution complete.')


def kill_descendents(signal_id):
    TRACE.write('In kill_self_and_descendents')
    try:
        pid = os.getpid()
        try:
            process = marcel.object.process.Process(pid)
            for p in process.descendents():
                TRACE.write(f'Killing descendent pid {p.pid}')
                p.kill(signal_id)
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
    config_path = (pathlib.Path(config_path)
                   if config_path else
                   pathlib.Path.home() / CONFIG_FILENAME).expanduser()
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
        env = input.load()
        namespace.update(env.namespace)
        env.namespace = namespace
        env.main_pid = os.getpid()
        pipeline = input.load()
        version = env.getvar('MARCEL_VERSION')
        TRACE.write(f'Marcel version {version}')
        TRACE.write(f'pipeline: {pipeline}')
        atexit.register(shutdown)
        pipeline.set_env(env)
        pipeline.set_error_handler(noop_error_handler)
        pipeline_runner = PipelineRunner(env, pipeline)
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
