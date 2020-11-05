import os

import marcel.main
import marcel.op
import marcel.object.host
import test_base

MAIN = marcel.main.Main(None, same_process=True, old_namespace=None)


class Bug30(test_base.Test):

    def __init__(self):
        """
        Initialize the state

        Args:
            self: (todo): write your description
        """
        super().__init__(MAIN)

    def setup(self):
        """
        Set up a new setup.

        Args:
            self: (todo): write your description
        """
        pass

    def run(self,
            test,
            verification=None,
            expected_out=None,
            expected_err=None,
            file=None):
        """
        Run the test.

        Args:
            self: (todo): write your description
            test: (bool): write your description
            verification: (todo): write your description
            expected_out: (str): write your description
            expected_err: (todo): write your description
            file: (str): write your description
        """
        self.setup()
        super().run(test, verification, expected_out, expected_err, file)


def main():
    """
    Main function.

    Args:
    """
    bug = Bug30()
    bug.cd('/tmp')
    bug.run(test='cd ~',
            verification='pwd',
            expected_out=['/home/jao'])
    print(f'Test failures: {bug.failures}')


main()
