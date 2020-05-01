import io
import dill
import subprocess
import sys

import marcel.core
import marcel.object.error


class Remote(marcel.core.Op):

    def __init__(self, pipeline):
        super().__init__()
        self.host = None
        self.pipeline = pipeline
        self.process = None

    def __repr__(self):
        return f'remote({self.host}, {self.pipeline})'

    # BaseOp

    def setup_1(self):
        pass

    def receive(self, _):
        # Start the remote process
        command = ' '.join([
            'ssh',
            '-l',
            self.host.user,
            self.host.ip_addr,
            'farcel.py'
        ])
        self.process = subprocess.Popen(command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        universal_newlines=False)
        # Pickle the pipeline so that it can be sent to the remote process
        buffer = io.BytesIO()
        pickler = dill.Pickler(buffer)
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
        input = dill.Unpickler(io.BytesIO(stdout))
        try:
            while True:
                x = input.load()
                if isinstance(x, marcel.exception.KillCommandException):
                    raise marcel.exception.KillCommandException(x.cause)
                self.send(x)
        except EOFError as e:
            self.send_complete()

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # Remote

    def set_host(self, host):
        self.host = host
