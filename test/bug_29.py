import os

import marcel.main
import marcel.op
import marcel.object.host
import test_base

MAIN = marcel.main.Main(None, same_process=True, old_namespace=None)


class Bug29(test_base.Test):

    def __init__(self):
        """
        Initialize the state

        Args:
            self: (todo): write your description
        """
        super().__init__(MAIN, './.marcel_bug29.py')

    def setup(self):
        """
        Setup the cdr

        Args:
            self: (todo): write your description
        """
        self.cd('/tmp')
        os.system('rm -rf /tmp/test')
        os.system('mkdir /tmp/test')
        self.cd('/tmp/test')
        os.system('echo asdf > f')
        os.system('mkdir d')

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
    Main function

    Args:
    """
    bug = Bug29()
    localhost = marcel.object.host.Host('localhost', None)
    bug.run(test='ls | map (f: f.render_compact())',
            expected_out=['.', 'd', 'f'])
    bug.run(test='@1 [ ls ]',
            expected_out=[(0, '.'), (0, 'd'), (0, 'f')])
    bug.run(test='@jao [ ls /tmp/test | map (f: f.render_compact()) ]',
            expected_out=[(localhost, '.'), (localhost, 'd'), (localhost, 'f')])
    bug.run(test='@jao [ ls /tmp/test ] | map (host, f: (host, f.render_compact()))',
            expected_out=[(localhost, '.'), (localhost, 'd'), (localhost, 'f')])
    print(f'Test failures: {bug.failures}')


main()
