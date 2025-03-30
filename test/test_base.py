import contextlib
import os
import pathlib
import sys
import shutil
import tempfile
import time

import dill.source

import marcel.env
import marcel.exception
import marcel.locations
import marcel.main
import marcel.object.error
import marcel.object.workspace
import marcel.util


TEST_TIMING = False


def timeit(f):
    def timetest():
        start = time.time()
        f()
        stop = time.time()
        usec = (stop - start) * 1000000
        print(f'TEST TIMING -- {f.__name__}: {usec}')
    return timetest if TEST_TIMING else f


class TestBase:
    start_dir = os.getcwd()
    test_home = '/tmp/test_home'
    test_stdout = f'{test_home}/test_stdout.txt'
    test_stderr = f'{test_home}/test_stderr.txt'

    def __init__(self, config_file='./.marcel.py', main=None):
        self.config_file = config_file
        self.main = main
        self.locations = None
        self.env = None
        self.failures = 0
        self.reset_environment()
        self.test_stdout = None
        self.test_stderr = None

    def reset_environment(self):
        if self.main is not None:
            self.main.shutdown()
        os.environ['HOME'] = TestBase.test_home
        self.locations = marcel.locations.Locations()
        shutil.rmtree(TestBase.test_home, ignore_errors=True)

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

    def tab_complete(self, line, text):
        return self.main.tab_completer.candidates(line, text)

    def description(self, x):
        return x if isinstance(x, str) else dill.source.getsource(x).split('\n')[0]

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

    def report_failures(self, label):
        print(f'{self.failures} failures: {label}')


class TestConsole(TestBase):

    def __init__(self, config_file='./.marcel.py'):
        super().__init__(config_file)

    def reset_environment(self, config_file='./.marcel.py'):
        super().reset_environment()
        workspace = marcel.object.workspace.Workspace.default()
        env = marcel.env.EnvironmentInteractive.create(self.locations, workspace)
        test_config = pathlib.Path(f'{TestBase.start_dir}/{config_file}').read_text()
        self.main = marcel.main.MainInteractive(old_main=None,
                                                env=env,
                                                workspace=workspace,
                                                testing=True,
                                                initial_config=test_config)
        self.env = env
        # marcel.main.initialize_persistent_config_and_data(env)
        self.env.dir_state().change_current_dir(TestBase.start_dir)
        os.system('sudo rm -f /tmp/farcel*.log')

    def run(self,
            test,
            verification=None,
            expected_out=None,
            expected_err=None,
            file=None):
        # test is the thing being tested. Usually it will produce output that can be used for verification.
        # For operations with side effects (e.g. rm), a separate verification command is needed.
        if verification is None and expected_out is None and expected_err is None and file is None:
            self.handle_reconfigure_exception(lambda: self.main.parse_and_run_command(test))
        else:
            print(f'TESTING: {self.description(test)}')
            try:
                if verification is None:
                    actual_out, actual_err = self.run_and_capture_output(test)
                else:
                    self.handle_reconfigure_exception(lambda: self.run_and_capture_output(test))
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
                marcel.util.print_stack_of_current_exception()
                self.failures += 1
            except marcel.exception.KillCommandException as e:
                print(f'{self.description(test)}: Terminated by KillCommandException: {e}', file=sys.__stderr__)

    def cd(self, path):
        self.main.parse_and_run_command(f'cd {path}')

    def run_and_capture_output(self, command):
        self.test_stdout = open(TestBase.test_stdout, 'w')
        self.test_stderr = open(TestBase.test_stderr, 'w')
        with contextlib.redirect_stdout(self.test_stdout), contextlib.redirect_stderr(self.test_stderr):
            self.main.parse_and_run_command(command)
        self.test_stdout = open(TestBase.test_stdout, 'r')
        self.test_stderr = open(TestBase.test_stderr, 'r')
        test_stdout_contents = ''.join(self.test_stdout.readlines())
        test_stderr_contents = ''.join(self.test_stderr.readlines())
        self.test_stdout.close()
        self.test_stderr.close()
        return test_stdout_contents, test_stderr_contents

    # For workspace testing
    def handle_reconfigure_exception(self, action):
        try:
            return action()
        except marcel.exception.ReconfigureException as e:
            self.main.shutdown(restart=True)
            self.env = marcel.env.EnvironmentInteractive.create(self.main.env.locations, e.workspace_to_open)
            self.main = marcel.main.MainInteractive(self.main,
                                                    self.env,
                                                    e.workspace_to_open,
                                                    testing=True)
            return None, None

    def report_error(self, *messages):
        self.failures += 1
        for message in messages:
            if type(message) is tuple:
                message = list(message)
            if type(message) is list:
                message = '\n'.join([str(m) for m in message])
            elif not isinstance(message, str):
                message = str(message)
            print(message, file=sys.__stdout__)


class TestAPI(TestBase):

    def __init__(self, main):
        super().__init__(config_file=None, main=main)
        # Don't do this at top-level. Otherwise, marcel.api's atexit call can interfere with main's.
        import marcel.api

    def reset_environment(self, config_file='./.marcel.py'):
        super().reset_environment()
        self.env = marcel.api._ENV
        try:
            os.mkdir(TestBase.test_home)
        except FileExistsError:
            pass
        self.env.dir_state().change_current_dir(TestBase.start_dir)

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
                    marcel.util.print_stack_of_current_exception()
                    self.failures += 1

    def run_and_capture_output(self, command):
        self.test_stdout = open(TestBase.test_stdout, 'w')
        self.test_stderr = open(TestBase.test_stderr, 'w')
        with contextlib.redirect_stdout(self.test_stdout), contextlib.redirect_stderr(self.test_stderr):
            try:
                actual_return = command()
            except marcel.exception.KillCommandException as e:
                print(f'{self.description(command)}: Terminated by KillCommandException: {e}', file=sys.stderr)
                actual_return = None
        self.test_stdout = open(TestBase.test_stdout, 'r')
        self.test_stderr = open(TestBase.test_stderr, 'r')
        test_stdout_contents = ''.join(self.test_stdout.readlines())
        test_stderr_contents = ''.join(self.test_stderr.readlines())
        self.test_stdout.close()
        self.test_stderr.close()
        return test_stdout_contents, test_stderr_contents, actual_return

    def check_eq(self, test, expected, actual):
        def match():
            if type(expected) != type(actual):
                return False
            if not marcel.util.is_sequence(expected):
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

    def reset_environment(self, config_file='./.marcel.py', new_main=False):
        super().reset_environment()
        workspace = marcel.object.workspace.Workspace.default()
        env = marcel.env.EnvironmentInteractive.create(self.locations, workspace)
        self.main = marcel.main.MainInteractive(old_main=None,
                                                env=env,
                                                workspace=workspace,
                                                testing=True)
        self.env = env
        self.env.dir_state().change_current_dir(TestBase.start_dir)
        os.system(f'cp {config_file} {self.locations.config_ws_startup(workspace)}')

    def run(self, line, expected=None):
        if expected is None:
            self.main.parse_and_run_command(line)
        else:
            print(f'TESTING: line=<<<{line}>>>')
            actual = self.main.tab_completer.candidates(line)
            if actual is None:
                actual = []
            if sorted(expected) != sorted(actual):
                print(f'    Expected: {sorted(expected)}')
                print(f'    Actual:   {sorted(actual)}')
                self.failures += 1


class TestDir(object):

    def __init__(self, env):
        self.env = env
        self.test_dir = pathlib.Path(tempfile.mkdtemp())

    def __enter__(self):
        return self.test_dir

    def __exit__(self, *_):
        # Remove references to the directory about to be nuked
        self.env.dir_state().reset_dir_stack()
        self.env.dir_state().change_current_dir('/tmp')
        os.system(f'rm -rf {self.test_dir.absolute()}')
