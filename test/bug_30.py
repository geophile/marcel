import os

import marcel.main
import marcel.op
import marcel.object.host
import test_base

MAIN = marcel.main.Main(None, same_process=True, old_namespace=None)


class Bug30(test_base.Test):

    def __init__(self):
        super().__init__(MAIN)

    def setup(self):
        pass

    def run(self,
            test,
            verification=None,
            expected_out=None,
            expected_err=None,
            file=None):
        self.setup()
        super().run(test, verification, expected_out, expected_err, file)


def main():
    bug = Bug30()
    bug.cd('/tmp')
    bug.run(test='cd ~',
            verification='pwd',
            expected_out=['/home/jao'])
    print(f'Test failures: {bug.failures}')


main()
