import contextlib
import io
import os
import pathlib

import marcel.exception
import marcel.util


class Test:

    start_dir = os.getcwd()

    def __init__(self, main, config_file='./.marcel.py'):
        self.main = main
        self.failures = 0
        self.reset_environment(config_file)

    def reset_environment(self, config_file='./.marcel.py'):
        os.system('sudo touch /tmp/farcel.log')
        os.system('sudo rm /tmp/farcel.log')
        os.chdir(Test.start_dir)
        self.main.global_state.env = marcel.env.Environment(config_file)

    def new_file(self, filename):
        path = pathlib.Path(filename)
        if path.exists():
            path.unlink()
        path.open()

    def check_ok(self, command, expected, actual):
        expected = self.remove_empty_line_at_end(expected.split('\n'))
        actual = self.remove_empty_line_at_end(actual.split('\n'))
        ok = True
        n = len(expected)
        if len(actual) == n:
            i = 0
            while ok and i < n:
                e = expected[i]
                a = actual[i]
                e_error = e.startswith('Error(') and e.endswith(')')
                a_error = a.startswith('Error(') and a.endswith(')')
                if e_error and a_error:
                    # Check that e message is a substring of a message
                    e_message = e[6:-1]
                    a_message = a[6:-1]
                    ok = e_message in a_message
                elif e_error or a_error:
                    ok = False
                else:
                    ok = a == e
                i += 1
        else:
            ok = False
        if not ok:
            print(f'{command} failed:')
            print(f'    expected:\n<<<{expected}>>>')
            print(f'    actual:\n<<<{actual}>>>')
            self.failures += 1

    def check_substring(self, command, expected, actual):
        if expected not in actual:
            print(f'{command} failed. Expected substring not found in actual:')
            print(f'    expected:\n<<<{expected}>>>')
            print(f'    actual:\n<<<{actual}>>>')
            self.failures += 1

    def fail(self, command, message):
        print(f'{command} failed: {message}')
        self.failures += 1

    def run_and_capture_output(self, command):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.main.run_command(command)
        return out.getvalue(), err.getvalue()

    def run(self,
            test,
            verification=None,
            expected_out=None,
            expected_err=None,
            file=None):
        # test is the thing being tested. Usually it will produce output that can be used for verification.
        # For operations with side effects (e.g. rm), a separate verification command is needed.
        if verification is None and expected_out is None and expected_err is None and file is None:
            self.main.run_command(test)
        else:
            print(f'TESTING: {test}')
            try:
                if verification is None:
                    actual_out, actual_err = self.run_and_capture_output(test)
                else:
                    self.run_and_capture_output(test)
                    actual_out, actual_err = self.run_and_capture_output(verification)
                if file:
                    actual_out = self.file_contents(file)
                if expected_out:
                    self.check_ok(test, self.to_string(expected_out), actual_out)
                if expected_err:
                    self.check_substring(test, expected_err, actual_err)
                elif actual_err:
                    self.fail(test, f'Unexpected error: {actual_err}')
            except Exception as e:
                print(f'{test}: Terminated by uncaught exception: {e}')
                marcel.util.print_stack()
                self.failures += 1
            except marcel.exception.KillCommandException as e:
                print(f'{test}: Terminated by KillCommandException: {e}')

    def file_contents(self, filename):
        file = open(filename, 'r')
        contents = ''.join(file.readlines())
        file.close()
        return contents

    def to_string(self, x):
        if isinstance(x, str):
            return x
        elif isinstance(x, tuple) or isinstance(x, list):
            return '\n'.join([str(o) for o in x]) + '\n'
        else:
            return str(x)

    def delete_file(self, filename):
        os.remove(filename)

    def remove_empty_line_at_end(self, lines):
        if len(lines[-1]) == 0:
            del lines[-1]
        return lines

    def cd(self, path):
        self.main.run_command(f'cd {path}')
