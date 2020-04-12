#!/usr/bin/python3

import os
import threading
import signal

import marcel.core
import marcel.env
import marcel.globalstate
import marcel.object.process
from marcel.util import *

# stdin carries the following from the client process:
#   - The pipeline to be executed
#   - Possibly a kill signal
# The kill signal may be delayed and may never arrive. Pipeline execution takes place
# on a thread so that stdin can be monitored for the kill signal and then acted upon.


TRACE = Trace('/tmp/farcel.log')


class PickleOutput(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.pickler = pickle.Pickler(sys.stdout.buffer)

    def setup_1(self):
        pass

    def receive(self, x):
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
        pipeline.append(PickleOutput())
        self.pipeline = pipeline

    def run(self):
        self.pipeline.setup_1()
        # Don't need setup_2, which is for nested pipelines. This is a nested pipeline, and we aren't
        # supporting more than one level of nesting.
        TRACE.write(f'PipelineRunner: About to run {self.pipeline}')
        try:
            self.pipeline.receive(None)
        except BaseException as e:
            TRACE.write(f'PipelineRunner.run caught {type(e)}: {e}')
            print_stack(file=TRACE.file)
            raise
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
            print_stack(TRACE.file)
    except BaseException as e:
        TRACE.write(f'Caught {type(e)} in kill_self_and_descendents: {e}')
        print_stack(TRACE.file)


def main():
    env = marcel.env.Environment(None)
    global_state = marcel.globalstate.GlobalState(env)
    # Use sys.stdin.buffer because we want binary data, not the text version
    input = pickle.Unpickler(sys.stdin.buffer)
    pipeline = input.load()
    pipeline.set_global_state(global_state)
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
        kill_descendents(signal.SIGKILL)
    finally:
        TRACE.write('Exiting')
        TRACE.close()


main()
