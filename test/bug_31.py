import os

import marcel.main
import marcel.op
import marcel.object.host
import test_base

MAIN = marcel.main.MainInteractive(None)


class Bug31(test_base.Test):

    def __init__(self):
        super().__init__(MAIN)

    def setup(self):
        self.cd('/tmp')
        os.system('rm -rf /tmp/test')
        os.system('mkdir /tmp/test')
        self.cd('/tmp/test')
        os.system('touch a b')

    def run(self,
            test,
            verification=None,
            expected_out=None,
            expected_err=None,
            file=None):
        self.setup()
        super().run(test, verification, expected_out, expected_err, file)


def main():
    bug = Bug31()
    bug.run(test='ls | map (f: f.render_compact())',
            expected_out=['.', 'a', 'b'])
    bug.run('ls /no/such/place | map (f: f.render_compact())',
            expected_err='No qualifying paths')
    bug.run('ls /no/such/place . | map (f: f.render_compact())',
            expected_out=['.', 'a', 'b'])
    print(f'Test failures: {bug.failures}')


main()
