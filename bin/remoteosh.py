#!/usr/bin/python3

import os
import threading
import signal

import marcel.core
import marcel.object.process
from marcel.util import *

# stdin carries the following from the client process:
#   - The pipeline to be executed
#   - Possibly a kill signal
# The kill signal may be delayed and may never arrive. Pipeline execution takes place
# on a thread so that stdin can be monitored for the kill signal and then acted upon.


TRACE = Trace('/tmp/remoteosh.log')


class PickleOutput(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.pickler = pickle.Pickler(sys.stdout.buffer)

    def setup_1(self):
        pass

    def receive(self, x):
        self.pickler.dump(x)

    def receive_error(self, error):
        TRACE.write('Pickling error: (%s) %s' % (type(error), error))
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
        TRACE.write('PipelineRunner: About to run %s' % self.pipeline)
        try:
            self.pipeline.receive(None)
        except BaseException as e:
            TRACE.write('PipelineRunner.run caught %s: %s' % (type(e), e))
            print_stack(file=TRACE.file)
            raise
        TRACE.write('PipelineRunner: Execution complete.')
        self.pipeline.receive_complete()


def kill_self_and_descendents(signal_id):
    TRACE.write('In kill_self_and_descendents')
    try:
        pid = os.getpid()
        try:
            process = marcel.object.process.Process(pid)
            for p in process.descendents:
                TRACE.write('Killing descendent pid %s' % p.pid)
                p.kill(signal_id)
            # TRACE.write('About to close stdout, closed = %s' % sys.stdout.closed)
            # sys.stdout.close()
            # TRACE.write('stdout closed, closed = %s' % sys.stdout.closed)
            # sys.stderr.close()
            # Suicide
            TRACE.write('Killing self, pid = %s' % pid)
            process.kill(signal_id)
        except Exception as e:
            TRACE.write('Caught exception while killing process %s and descendents: %s' % (pid, e))
            print_stack(TRACE.file)
    except BaseException as e:
        TRACE.write('Caught %s in kill_self_and_descendents: %s' % (type(e), e))
        print_stack(TRACE.file)


def main():
    marcel.env.Environment.initialize(None)
    # Use sys.stdin.buffer because we want binary data, not the text version
    input = pickle.Unpickler(sys.stdin.buffer)
    pipeline = input.load()
    TRACE.write('pipeline: %s' % pipeline)
    pipeline_runner = PipelineRunner(pipeline)
    pipeline_runner.start()
    try:
        signal_id = input.load()
        TRACE.write('Received signal %s' % signal_id)
        kill_self_and_descendents(signal_id)
    except EOFError:
        TRACE.write('Received EOF')
        while pipeline_runner.is_alive():
            TRACE.write('PipelineRunner alive: %s' % pipeline_runner.is_alive())
            pipeline_runner.join(0.1)
        TRACE.write('PipelineRunner alive: %s' % pipeline_runner.is_alive())
        kill_self_and_descendents(signal.SIGKILL)
    finally:
        TRACE.write('Exiting')
        TRACE.close()


main()
