import marcel.main
import marcel.object.host
import test_base

MAIN = marcel.main.Main(None, same_process=True, old_namespace=None)


class Bug38(test_base.Test):

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
    Run the bugzilla test.

    Args:
    """
    bug = Bug38()
    bug.run(test='bash ls /var/log/syslog* | wc -l | map (x: int(x) > 0)',
            expected_out=[True])
    print(f'Test failures: {bug.failures}')


main()
