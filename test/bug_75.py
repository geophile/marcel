import test_base


# grammar.txt starts like this:
#
# command:
#         assignment
#         pipeline
#
# assignment:
#         var = [ pipeline ]
#         var = expr
#         var = str
#
# Bug 75 causes the read op to miss the "assignment:" line and everything after.

class Bug75(test_base.TestConsole):

    def __init__(self):
        """
        Initialize the state

        Args:
            self: (todo): write your description
        """
        super().__init__()

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
    Runs a bug.

    Args:
    """
    bug = Bug75()
    bug.run('ls ../notes/grammar.txt | read')


main()
