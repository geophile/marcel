import marcel.helpformatter
import marcel.main
import marcel.object.host
import marcel.util
import test_base

MAIN = marcel.main.Main(None, same_process=True, old_namespace=None)

TEXT = '''
If this sequence is piped to this invocation of {red}:

    red . + . +

then groups are defined using the first and third values, {(1, 10), (1, 11), (2, 20), (3, 30)}.
The output would be:

    (1, 11, 10, 300)
'''


class Bug39(test_base.Test):

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
    bug = Bug39()
    formatter = marcel.helpformatter.Helpformatter(MAIN.env.color_scheme())
    formatted = formatter.format(TEXT)
    print(formatted)


main()
