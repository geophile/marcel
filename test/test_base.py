import contextlib
import os
import pathlib
import sys
import shutil

import dill.source

import marcel.exception
import marcel.main
import marcel.object.error
import marcel.util


TEST_STDOUT = '/tmp/test_stdout.txt'
TEST_STDERR = '/tmp/test_stderr.txt'


class TestBase:
    start_dir = os.getcwd()

    def __init__(self, config_file='./.marcel.py', main=None):
        self.config_file = config_file
        self.main = main
        self.env = None
        self.failures = 0
        self.reset_environment(config_file)
        self.test_stdout = None
        self.test_stderr = None

    def reset_environment(self, config_file='./.marcel.py', new_main=False):
        if self.main is None or new_main:
            self.main = marcel.main.Main(config_file, same_process=True, old_namespace=None)
        self.env = self.main.env
        os.system('sudo touch /tmp/farcel.log')
        os.system('sudo rm /tmp/farcel.log')
        os.chdir(TestConsole.start_dir)

    def new_file(self, filename):
        path = pathlib.Path(filename)
        if path.exists():
            path.unlink()
        path.open()

    def fail(self, command, message):
        print(f'{self.description(command)} failed: {message}', file=sys.__stdout__)
        self.failures += 1

    def file_contents(self, filename):
        file = open(filename, 'r')
        contents = ''.join(file.readlines())
        file.close()
        return contents

    def to_string(self, x):
        if isinstance(x, str):
            return x
        elif isinstance(x, tuple) or isinstance(x, list):
            return '\n'.join([str(o) for o in x])
        else:
            return str(x)

    def delete_files(self, *filenames):
        for filename in filenames:
            try:
                os.remove(filename)
            except IsADirectoryError:
                shutil.rmtree(filename)
            except FileNotFoundError:
                pass

    def remove_empty_line_at_end(self, lines):
        if len(lines[-1]) == 0:
            del lines[-1]
        return lines

    def cd(self, path):
        self.main.run_command(f'cd {path}')

    def tab_complete(self, line, text):
        return self.main.tab_completer.candidates(line, text)

    def description(self, x):
        return x if type(x) is str else dill.source.getsource(x).split('\n')[0]

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
                e_error = e.startswith('Error')
                a_error = a.startswith('Error')
                if e_error and a_error:
                    # Check that e message is a substring of a message
                    e_message = e[e.find(': ')+2:]
                    a_message = a[e.find(': ')+2:]
                    ok = e_message in a_message
                elif e_error or a_error:
                    ok = False
                else:
                    ok = a == e
                i += 1
        else:
            ok = False
        if not ok:
            print(f'{self.description(command)} failed:', file=sys.__stdout__)
            print(f'    expected:\n<<<{expected}>>>', file=sys.__stdout__)
            print(f'    actual:\n<<<{actual}>>>', file=sys.__stdout__)
            self.failures += 1

    def check_substring(self, command, expected, actual):
        if expected not in actual:
            print(f'{self.description(command)} failed. Expected substring not found in actual:', file=sys.__stdout__)
            print(f'    expected:\n<<<{expected}>>>', file=sys.__stdout__)
            print(f'    actual:\n<<<{actual}>>>', file=sys.__stdout__)
            self.failures += 1


class TestConsole(TestBase):

    def __init__(self, config_file='./.marcel.py'):
        super().__init__(config_file)

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
            print(f'TESTING: {self.description(test)}')
            try:
                if verification is None:
                    actual_out, actual_err = self.run_and_capture_output(test)
                else:
                    self.run_and_capture_output(test)
                    actual_out, actual_err = self.run_and_capture_output(verification)
                if file:
                    actual_out = self.file_contents(file)
                if actual_err is not None and len(actual_err) > 0 and expected_err is None:
                    self.fail(test, f'Unexpected error: {actual_err}')
                if expected_out:
                    self.check_ok(test, self.to_string(expected_out), actual_out)
                if expected_err:
                    self.check_substring(test, expected_err, actual_err)
            except Exception as e:
                print(f'{self.description(test)}: Terminated by uncaught exception: {e}', file=sys.__stdout__)
                marcel.util.print_stack()
                self.failures += 1
            except marcel.exception.KillCommandException as e:
                print(f'{self.description(test)}: Terminated by KillCommandException: {e}', file=sys.__stderr__)

    def run_and_capture_output(self, command):
        self.test_stdout = open(TEST_STDOUT, 'w')
        self.test_stderr = open(TEST_STDERR, 'w')
        with contextlib.redirect_stdout(self.test_stdout), contextlib.redirect_stderr(self.test_stderr):
            self.main.run_command(command)
        self.test_stdout = open(TEST_STDOUT, 'r')
        self.test_stderr = open(TEST_STDERR, 'r')
        test_stdout_contents = ''.join(self.test_stdout.readlines())
        test_stderr_contents = ''.join(self.test_stderr.readlines())
        self.test_stdout.close()
        self.test_stderr.close()
        return test_stdout_contents, test_stderr_contents

    def expect_config_change_exception(self):
        try:
            self.run('pwd | select (*x: False)')
            self.fail('pwd', 'Should have triggered ReloadConfigException')
        except marcel.main.ReloadConfigException:
            self.reset_environment(self.config_file)


class TestAPI(TestBase):

    def __init__(self, config_file='./.marcel.py', main=None):
        super().__init__(config_file=config_file, main=main)

    def run(self,
            test,
            verification=None,
            expected_out=None,
            expected_err=None,
            expected_return=None,
            expected_errors=None,
            actual_errors=None,
            expected_exception=None,
            file=None):
        # test is the thing being tested. Usually it will produce output that can be used for verification.
        # For operations with side effects (e.g. rm), a separate verification command is needed.
        if (verification is None and
                expected_out is None and
                expected_err is None and
                expected_return is None and
                expected_errors is None and
                expected_exception is None and
                file is None):
            test()
        else:
            print(f'TESTING: {self.description(test)}')
            try:
                if verification is None:
                    actual_out, actual_err, actual_return = self.run_and_capture_output(test)
                else:
                    self.run_and_capture_output(test)
                    actual_out, actual_err, actual_return = self.run_and_capture_output(verification)
                if file:
                    actual_out = self.file_contents(file)
                if expected_out is not None:
                    if len(actual_err) > 0:
                        print(f'Unexpected error output: {actual_err}')
                    else:
                        self.check_ok(test, self.to_string(expected_out), actual_out)
                if expected_err is not None:
                    self.check_substring(test, expected_err, actual_err)
                if expected_return is not None:
                    if len(actual_err) > 0:
                        print(f'Unexpected error output: {actual_err}')
                    else:
                        self.check_eq(test, expected_return, actual_return)
                assert (expected_errors is None) == (actual_errors is None)
                if expected_errors is not None:
                    self.check_eq(test, expected_errors, actual_errors)
            except Exception as e:
                if expected_exception is None:
                    print(f'{self.description(test)}: Terminated by uncaught exception: {e}', file=sys.__stdout__)
                    self.failures += 1
                elif expected_exception not in str(e):
                    print(f'{self.description(test)}: Terminated by unexpected exception: {e}', file=sys.__stdout__)
                    marcel.util.print_stack()
                    self.failures += 1

    def run_and_capture_output(self, command):
        self.test_stdout = open(TEST_STDOUT, 'w')
        self.test_stderr = open(TEST_STDERR, 'w')
        with contextlib.redirect_stdout(self.test_stdout), contextlib.redirect_stderr(self.test_stderr):
            try:
                actual_return = command()
            except marcel.exception.KillCommandException as e:
                print(f'{self.description(command)}: Terminated by KillCommandException: {e}', file=sys.stderr)
                actual_return = None
        self.test_stdout = open(TEST_STDOUT, 'r')
        self.test_stderr = open(TEST_STDERR, 'r')
        test_stdout_contents = ''.join(self.test_stdout.readlines())
        test_stderr_contents = ''.join(self.test_stderr.readlines())
        self.test_stdout.close()
        self.test_stderr.close()
        return test_stdout_contents, test_stderr_contents, actual_return

    def check_eq(self, test, expected, actual):
        def match():
            if type(expected) != type(actual):
                return False
            if not marcel.util.is_sequence_except_string(expected):
                return expected == actual
            if type(expected) is marcel.object.error.Error:
                return expected.message in actual.message
            if len(expected) != len(actual):
                return False
            for i in range(len(expected)):
                e = expected[i]
                a = actual[i]
                if type(e) != type(a):
                    return False
                if type(e) is marcel.object.error.Error:
                    if e.message not in a.message:
                        return False
                elif e != a:
                    return False
            return True

        if not match():
            print(f'{self.description(test)} failed, expected != actual:', file=sys.__stdout__)
            print(f'    expected:\n<<<{expected}>>>', file=sys.__stdout__)
            print(f'    actual:\n<<<{actual}>>>', file=sys.__stdout__)
            self.failures += 1


class TestTabCompletion(TestBase):

    def __init__(self, config_file='./.marcel.py'):
        super().__init__(config_file)

    def reset_environment(self, config_file='./.marcel.py'):
        self.main = marcel.main.Main(config_file, same_process=True, old_namespace=None)

    def run(self, line, text=None, expected=None):
        if text is None:
            self.main.run_command(line)
        else:
            print(f'TESTING: line="{line}", text="{text}"')
            actual = self.main.tab_completer.candidates(line, text)
            if actual is None:
                actual = []
            if sorted(expected) != sorted(actual):
                print(f'    Expected: {sorted(expected)}')
                print(f'    Actual:   {sorted(actual)}')
                self.failures += 1
