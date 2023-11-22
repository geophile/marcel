import os

import marcel.main
import marcel.op
import marcel.object.cluster
import test_base

MAIN = marcel.main.MainInteractive(None)


class Bug33(test_base.Test):

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
    bug = Bug33()
    bug.run('git diff > /dev/null')
    print(f'Test failures: {bug.failures}')


main()
