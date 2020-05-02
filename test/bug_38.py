import marcel.main
import marcel.object.host
import test_base

MAIN = marcel.main.Main(same_process=True)


class Bug38(test_base.Test):

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
    bug = Bug38()
    bug.run(test='bash ls /var/log/syslog* | wc -l | map (x: int(x) > 0)',
            expected_out=[True])
    print(f'Test failures: {bug.failures}')


main()
