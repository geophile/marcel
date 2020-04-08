import argparse
import io
import pickle
import subprocess
import sys

import marcel.core


def sudo():
    return Sudo()


class SudoArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('sudo')
        self.add_argument('args', nargs=argparse.REMAINDER)


class Sudo(marcel.core.Op):

    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self.args = None

    def __repr__(self):
        return f'sudo({self.pipeline})'

    # BaseOp

    def setup_1(self):
        pass

    def receive(self, _):
        # Start the remote process
        command = ' '.join(['sudo'] + self.args + ['farcel.py'])
        self.process = subprocess.Popen(command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        universal_newlines=False)
        # Pickle the pipeline so that it can be sent to the remote process
        buffer = io.BytesIO()
        pickler = pickle.Pickler(buffer)
        pickler.dump(self.pipeline)
        buffer.seek(0)
        stdout, stderr = self.process.communicate(input=buffer.getvalue())
        # Wait for completion (already guaranteed by communicate returning?)
        self.process.wait()
        # Handle results
        stderr_lines = stderr.decode('utf-8').split('\n')
        if len(stderr_lines[-1]) == 0:
            del stderr_lines[-1]
        for line in stderr_lines:
            print(line, file=sys.stderr)
        input = pickle.Unpickler(io.BytesIO(stdout))
        try:
            while True:
                self.send(input.load())
        except EOFError:
            self.send_complete()

    # Op

    def must_be_first_in_pipeline(self):
        return True
