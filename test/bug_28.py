import os

import marcel.main
import marcel.op
import marcel.object.host
import test_base

MAIN = marcel.main.Main(same_process=True, old_namespace=None)


class Bug28(test_base.Test):

    def __init__(self):
        super().__init__(MAIN)

    def setup(self):
        self.cd('/tmp')
        os.system('rm -rf /tmp/test')
        os.system('mkdir /tmp/test')
        self.cd('/tmp/test')
        os.system('echo asdf > f')

    def run(self,
            test,
            verification=None,
            expected_out=None,
            expected_err=None,
            file=None):
        self.setup()
        super().run(test, verification, expected_out, expected_err, file)


def main():
    bug = Bug28()
    bug.run(test='ls | map (f: f))',
            expected_err='Unmatched )')
    print(f'Test failures: {bug.failures}')


main()
