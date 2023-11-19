import test_base


# grammar.txt starts like this:
#
# command:
#         assignment
#         pipelines
#
# assignment:
#         var = [ pipelines ]
#         var = expr
#         var = str
#
# Bug 75 causes the read op to miss the "assignment:" line and everything after.

class Bug75(test_base.TestConsole):

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
    bug = Bug75()
    bug.run('ls ../notes/grammar.txt | read')


main()
