import subprocess
import io
import pickle
import sys

import osh.ssh


class Remote(osh.core.Op):

    def __init__(self, host, pipeline):
        super().__init__()
        self.host = host
        self.pipeline = pipeline
        self.process = None

    def __repr__(self):
        return 'remote()'

    # BaseOp

    def setup_1(self):
        command = [
            'ssh',
            self.host.ip_addr,
            '-l',
            self.host.user,
            'remoteosh.py'
        ]
        self.process = subprocess.Popen(command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        universal_newlines=False)
        buffer = io.BytesIO()
        pickler = pickle.Pickler(buffer)
        pickler.dump(self.pipeline)
        buffer.seek(0)
        self.process.stdin.write(buffer.read())
        self.process.stdin.close()

    def execute(self):
        self.process.wait()
        stderr = self.process.stderr.read().decode('utf-8').split('\n')
        for line in stderr:
            print(line, file=sys.stderr)
        stdout = pickle.Unpickler(self.process.stdout.read()).load()
        for x in stdout:
            self.send(x)
        self.send_complete()
