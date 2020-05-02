import marcel.helpformatter
import marcel.main
import marcel.object.host
import marcel.util
import test_base

MAIN = marcel.main.Main(same_process=True)

TEXT = '''
If this sequence is piped to this invocation of {red}:

    red . + . +

then groups are defined using the first and third values, {(1, 10), (1, 11), (2, 20), (3, 30)}.
The output would be:

    (1, 11, 10, 300)
'''


class Bug39(test_base.Test):

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
    bug = Bug39()
    formatter = marcel.helpformatter.Helpformatter(MAIN.env.color_scheme())
    formatted = formatter.format(TEXT)
    print(formatted)


main()
