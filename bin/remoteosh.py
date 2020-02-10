#!/usr/bin/python3

import os
import sys
import io
import pickle
import threading
import signal

import osh.core
import osh.object.process

# stdin carries the following from the client process:
#   - The pipeline to be executed
#   - Possibly a kill signal
# The kill signal may be delayed and may never arrive. Pipeline execution takes place
# on a thread so that stdin can be monitored for the kill signal and then acted upon.


class PickleOutput(osh.core.Op):

    def __init__(self):
        super().__init__()
        self.pickler = pickle.Pickler(io.BytesIO())

    def setup(self):
        pass

    def receive(self, x):
        self.pickler.dump(x)

    def receive_complete(self):
        pass


class PipelineRunner(threading.Thread):

    def __init__(self, pipeline):
        super().__init__()
        pipeline.append(PickleOutput())
        self.pipeline = pipeline

    def run(self):
        self.pipeline.setup_1()
        # Don't need setup_2, which is for nested pipelines. This is a nested pipeline, and we aren't
        # supporting more than one level of nesting.
        self.pipeline.execute()
        self.pipeline.receive_complete()


def kill_self_and_descendents(signal_id):
    pid = os.getpid()
    try:
        process = osh.object.process.Process(pid)
        for p in process.descendents:
            p.kill(signal_id)
        process.kill(signal_id)
    except Exception as e:
        print('Caught exception while killing process %s and descendents: %s' % (pid, e))


def main():
    input = pickle.Unpickler(sys.stdin)
    pipeline = input.load()
    pipeline_runner = PipelineRunner(pipeline)
    pipeline_runner.start()
    try:
        signal_id = input.load()
        kill_self_and_descendents(signal_id)
    except EOFError:
        # Client closed the socket, so kill won't arrive. The thread executing the pipeline
        # should have ended, so kill if it hasn't.
        pipeline_runner.join(0.1)
        if pipeline_runner.is_alive():
            kill_self_and_descendents(signal.SIGKILL)


main()
