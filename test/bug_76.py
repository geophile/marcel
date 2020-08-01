import os

import test_base


class Bug76(test_base.TestConsole):

    def __init__(self):
        super().__init__()

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
    bug = Bug76()
    os.system('rm ~/bug_76.txt')
    bug.run('gen 3 | out -f ~/bug_76.txt')


main()
