#!python

import os
import dill
import threading
import signal
import sys

import marcel.core
import marcel.env
import marcel.object.error
import marcel.object.process
import marcel.util

# stdin carries the following from the client process:
#   - The pipeline to be executed
#   - Possibly a kill signal
# The kill signal may be delayed and may never arrive. Pipeline execution takes place
# on a thread so that stdin can be monitored for the kill signal and then acted upon.


TRACE = marcel.util.Trace('/tmp/farcel.log')


class PickleOutput(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.pickler = dill.Pickler(sys.stdout.buffer)

    def __repr__(self):
        return 'pickleoutput()'

    def setup_1(self):
        pass

    def receive(self, x):
        # TRACE.write(f'Pickling: ({type(x)}) {x}')
        self.pickler.dump(x)

    def receive_error(self, error):
        TRACE.write(f'Pickling error: ({type(error)}) {error}')
        self.pickler.dump(error)
        super().receive_error(error)

    def receive_complete(self):
        TRACE.write('Closing stdout')
        sys.stdout.buffer.close()


class PipelineRunner(threading.Thread):

    def __init__(self, pipeline):
        super().__init__()
        self.pickler = PickleOutput()
        pipeline.append(self.pickler)
        self.pipeline = pipeline

    def run(self):
        try:
            TRACE.write(f'PipelineRunner: About to setup1 {self.pipeline}')
            self.pipeline.setup_1()
            # Don't need setup_2, which is for nested pipelines. This is a nested pipeline, and we aren't
            # supporting more than one level of nesting.
            TRACE.write(f'PipelineRunner: About to run {self.pipeline}')
            self.pipeline.receive_input(None)
        except BaseException as e:
            TRACE.write(f'PipelineRunner.run caught {type(e)}: {e}')
            marcel.util.print_stack(file=TRACE.file)
            self.pickler.receive_error(e)
        self.pipeline.receive_complete()
        TRACE.write('PipelineRunner: Execution complete.')


def kill_descendents(signal_id):
    TRACE.write('In kill_self_and_descendents')
    try:
        pid = os.getpid()
        try:
            process = marcel.object.process.Process(pid)
            for p in process.descendents:
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


def main():
    def noop_error_handler(env, error):
        pass

    env = marcel.env.Environment(None)
    version = env.getvar('MARCEL_VERSION')
    TRACE.write(f'Marcel version {version}')
    # Use sys.stdin.buffer because we want binary data, not the text version
    input = dill.Unpickler(sys.stdin.buffer)
    pipeline = input.load()
    pipeline.set_env(env)
    pipeline.set_error_handler(noop_error_handler)
    TRACE.write(f'pipeline: {pipeline}')
    pipeline_runner = PipelineRunner(pipeline)
    pipeline_runner.start()
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
