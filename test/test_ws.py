import os
import pathlib
import sys

import psutil

import marcel.exception
import marcel.object.cluster
import marcel.object.error
import marcel.object.workspace
import marcel.version
from marcel.persistence.persistence import validate_all

import test_base

Workspace = marcel.object.workspace.Workspace
ValidationError = marcel.object.workspace.WorkspaceValidater.Error
timeit = test_base.timeit
TestDir = test_base.TestDir

Error = marcel.object.error.Error
start_dir = os.getcwd()
TEST = test_base.TestConsole()


def check_validation(actual, *expected):
    ok = len(actual) == len(expected)
    if ok:
        for validation_error in actual:
            match = False
            for expected_error in expected:
                match = (match or
                         (expected_error.workspace_name == validation_error.workspace_name and
                          expected_error.message in validation_error.message))
            ok = ok and match
            if not ok:
                break
    if not ok:
        TEST.report_error('Workspace validation error mismatch:',
                          'ACTUAL', actual,
                          'EXPECTED', expected)


def expect_exception(f, exception_class, expected_message):
    try:
        f()
        TEST.report_error(f'Expected {exception_class}: {expected_message}, '
                          f'but no exception was raised.')
    except BaseException as e:
        if not (isinstance(e, exception_class) and expected_message in str(e)):
            TEST.report_error(f'Expected {exception_class}: {expected_message}, '
                              f'got {e}')


@timeit
def test_workspace_lifecycle():
    TEST.reset_environment()
    # Starting state: There is only a default workspace, and it is the current workspace.
    TEST.run('ws | (w: w.is_default())',
             expected_out=[True])
    TEST.run('ws -l',
             expected_out=['Workspace()'])
    # Create a new workspace
    TEST.run(test='ws -n hello',
             verification='ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    TEST.run('ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    TEST.run('ws -l | (w: str(w)) | sort',
             expected_out=['Workspace()', 'Workspace(hello)'])
    # Creating it again should fail
    TEST.run(test='ws -n hello',
             expected_err='hello already exists')
    # Close the workspace. We should be back in default.
    TEST.run(test='ws -c',
             verification='ws | (w: w.is_default())',
             expected_out=[True])
    TEST.run('ws -l | (w: str(w)) | sort',
             expected_out=['Workspace()', 'Workspace(hello)'])
    # Closing the default workspace is a noop
    TEST.run(test='ws -c',
             verification='ws | (w: w.is_default())',
             expected_out=[True])
    TEST.run('ws -l | (w: str(w)) | sort',
             expected_out=['Workspace()', 'Workspace(hello)'])
    # Switch to the new workspace
    TEST.run(test='ws hello',
             verification='ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    # A variable in the workspace shouldn't be present in a different one
    TEST.run('ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    TEST.run('hellovar = world')
    TEST.run('env hellovar',
             expected_out=[('hellovar', 'world')])
    TEST.run(test='ws -c',
             verification='env hellovar',
             expected_err='hellovar is undefined')
    TEST.run(test='ws hello',
             verification='env hellovar',
             expected_out=[('hellovar', 'world')])
    # A module imported into the workspace shouldn't be present in a different one.
    TEST.run(test='ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    TEST.run(test='import os',
             verification='(os.__name__)',
             expected_out=['os'])
    TEST.run(test='ws -c',
             verification='(os.__name__)',
             expected_out=[Error('not defined')])
    TEST.run(test='ws hello',
             verification='(os.__name__)',
             expected_out=['os'])
    # Close and reopen, to make sure that workspace contents (vars, imports) reach disk if they came from disk in
    # the first place.
    TEST.run(test='ws -c',
             verification='ws | (w: str(w))',
             expected_out=['Workspace()'])
    TEST.run(test='ws hello',
             verification='ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    TEST.run(test='env hellovar',
             expected_out=[('hellovar', 'world')])
    TEST.run(test='(os.__name__)',
             expected_out=['os'])
    # Reopening the current workspace is a noop
    TEST.run(test='ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    TEST.run(test='env hellovar',
             expected_out=[('hellovar', 'world')])
    TEST.run(test='ws hello',
             verification='ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    TEST.run(test='ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    TEST.run(test='env hellovar',
             expected_out=[('hellovar', 'world')])
    # Deletion
    TEST.run(test='ws hello',
             verification='ws | (w: str(w))',
             expected_out=['Workspace(hello)'])
    TEST.run(test='ws -d hello',
             expected_err='cannot be deleted')
    TEST.run(test='ws -l | (w: str(w)) | sort',
             expected_out=['Workspace()', 'Workspace(hello)'])
    TEST.run(test='ws -d hello',
             expected_err='cannot be deleted')
    TEST.run(test='ws -c',
             verification='ws | (w: str(w))',
             expected_out=['Workspace()'])
    TEST.run(test='ws -d hello',
             expected_out=[])
    TEST.run(test='ws -l | (w: str(w))',
             expected_out=['Workspace()'])
    TEST.run(test='ws hello',
             expected_err='no workspace named hello')
    # Workspace that does not exist.
    TEST.run(test='ws this_is_not_a_workspace',
             expected_err='There is no workspace')
    TEST.run(test='ws -d this_is_not_a_workspace',
             expected_err='There is no workspace')


@timeit
def test_workspaces_and_reservoirs():
    TEST.reset_environment()
    ws_default = Workspace.default()
    ws_restest = Workspace('restest')
    # Default reservoir including its location
    TEST.run(test='gen 3 >$ g3_default',
             verification='g3_default <$',
             expected_out=[0, 1, 2])
    TEST.run(test=f'ls -f {TEST.locations.data_ws_res(ws_default, "g3_default")} | red count',
             expected_out=[1])
    # Leave the default workspace and check that the reservoir disappears
    TEST.run(test='ws -n restest',
             verification='ws',
             expected_out=['Workspace(restest)'])
    # Create a reservoir in the restest workspace
    TEST.run(test='gen 3 >$ g3_restest',
             verification='g3_restest <$',
             expected_out=[0, 1, 2])
    TEST.run(test=f'ls {TEST.locations.data_ws_res(ws_restest, "g3_restest")} | (f: f.as_posix())',
             expected_out=[f'{TEST.locations.data_ws_res(ws_restest, "g3_restest")}'])
    # Go back to the default workspace and check the reservoirs
    TEST.run(test='ws -c',
             verification='ws | (w: str(w))',
             expected_out=['Workspace()'])
    TEST.run(test=f'ls -f {TEST.locations.data_ws_res(ws_default)} | red count',
             expected_out=[1])
    TEST.run(test=f'ls -f {TEST.locations.data_ws_res(ws_restest)} | red count',
             expected_out=[1])
    # Re-enter restest, check again
    TEST.run(test='ws restest',
             verification='ws | (w: str(w))',
             expected_out=['Workspace(restest)'])
    TEST.run(test=f'ls -f {TEST.locations.data_ws_res(ws_default)} | red count',
             expected_out=[1])
    TEST.run(test=f'ls -f {TEST.locations.data_ws_res(ws_restest)} | red count',
             expected_out=[1])
    # And contents
    TEST.run(test='g3_restest <$',
             expected_out=[0, 1, 2])


@timeit
def test_workspaces_and_compilables():
    # Pipelines and functions are Compilables, and require special handling, since they aren't persisted as is.
    # Instead, their source is persisted, and they are recompiled when necessary, e.g. when switching to a workspace
    # whose environment stores them.
    TEST.reset_environment()
    TEST.run(test='ws -n w',
             verification='ws | (w: str(w))',
             expected_out=['Workspace(w)'])
    TEST.run(test='f = (lambda: lambda f: f + 1)',
             verification='(f(4))',
             expected_out=[5])
    TEST.run(test='g3 = (| gen 3 |)',
             verification='g3',
             expected_out=[0, 1, 2])
    TEST.run(test='gn = (| n: gen (int(n)) |)',
             verification='gn 5',
             expected_out=[0, 1, 2, 3, 4])
    # Close the workspace, make sure the vars we've just defined aren't there
    TEST.run(test='ws -c',
             verification='ws | (w: str(w))',
             expected_out=['Workspace()'])
    TEST.run(test='(f(5))',
             expected_out=[Error('not defined')])
    TEST.run(test='g3',
             expected_err='not executable')
    TEST.run(test='gn 4',
             expected_err='not executable')
    # Re-open the workspace, check that everything works
    TEST.run(test='ws w',
             verification='ws | (w: str(w))',
             expected_out=['Workspace(w)'])
    TEST.run(test='(f(4))',
             expected_out=[5])
    TEST.run(test='g3',
             expected_out=[0, 1, 2])
    TEST.run(test='gn 5',
             expected_out=[0, 1, 2, 3, 4])


@timeit
def test_workspace_validation():
    def validation_error_handler(broken_workspace_names, errors):
        pass

    TEST.reset_environment()
    # No workspaces
    check_validation(validate_all(TEST.env, validation_error_handler))
    # Create and check a good workspace
    TEST.run('ws -n w1')
    # ... while open
    check_validation(validate_all(TEST.env, validation_error_handler))
    # ... and closed
    TEST.run('ws -c')
    check_validation(validate_all(TEST.env, validation_error_handler))
    # Simulate an unclean shutdown by attaching a pid to the marker's filename.
    # Validation should fix things up.
    unused_pid = max(psutil.pids()) + 1000
    marker_file = pathlib.Path(f'{TEST.test_home}/.config/marcel/workspace/w1/.WORKSPACE')
    marker_file.rename(f'{marker_file}.{unused_pid}')
    check_validation(validate_all(TEST.env, validation_error_handler))
    os.system(f'rm -rf {TEST.test_home}/.config/marcel/workspace/w1')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w1')
    # Remove the startup file
    TEST.run('ws -n w2')
    TEST.run('ws -c')
    os.system(f'rm {TEST.test_home}/.config/marcel/workspace/w2/startup.py')
    check_validation(validate_all(TEST.env, validation_error_handler),
                     ValidationError('w2', 'startup.py is missing'))
    os.system(f'rm -rf {TEST.test_home}/.config/marcel/workspace/w2')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w2')
    # Remove the config directory
    TEST.run('ws -n w3')
    TEST.run('ws -c')
    os.system(f'rm -rf {TEST.test_home}/.config/marcel/workspace/w3')
    check_validation(validate_all(TEST.env, validation_error_handler),
                     ValidationError('w3', 'w3 is missing'))
    os.system(f'rm -rf {TEST.test_home}/.config/marcel/workspace/w3')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w3')
    # Remove the env.pickle file
    TEST.run('ws -n w4')
    TEST.run('ws -c')
    os.system(f'rm {TEST.test_home}/.local/share/marcel/workspace/w4/env.pickle')
    check_validation(validate_all(TEST.env, validation_error_handler),
                     ValidationError('w4', 'env.pickle is missing'))
    os.system(f'rm -rf {TEST.test_home}/.config/marcel/workspace/w4')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w4')
    # Remove the env.pickle file
    TEST.run('ws -n w5')
    TEST.run('ws -c')
    os.system(f'rm {TEST.test_home}/.local/share/marcel/workspace/w5/properties.pickle')
    check_validation(validate_all(TEST.env, validation_error_handler),
                     ValidationError('w5', 'properties.pickle is missing'))
    os.system(f'rm -rf {TEST.test_home}/.config/marcel/workspace/w5')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w5')
    # Remove the history file
    TEST.run('ws -n w6')
    TEST.run('ws -c')
    os.system(f'rm {TEST.test_home}/.local/share/marcel/workspace/w6/history')
    check_validation(validate_all(TEST.env, validation_error_handler),
                     ValidationError('w6', 'history is missing'))
    os.system(f'rm -rf {TEST.test_home}/.config/marcel/workspace/w6')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w6')
    # Remove the reservoirs directory
    TEST.run('ws -n w7')
    TEST.run('ws -c')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w7/reservoirs')
    check_validation(validate_all(TEST.env, validation_error_handler),
                     ValidationError('w7', 'reservoirs is missing'))
    os.system(f'rm -rf {TEST.test_home}/.config/marcel/workspace/w7')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w7')
    # Remove the data directory
    TEST.run('ws -n w8')
    TEST.run('ws -c')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w8')
    check_validation(validate_all(TEST.env, validation_error_handler),
                     ValidationError('w8', 'w8 is missing'))
    os.system(f'rm -rf {TEST.test_home}/.config/marcel/workspace/w8')
    os.system(f'rm -rf {TEST.test_home}/.local/share/marcel/workspace/w8')
    # Not workspace-related, but this is a convenient place to check VERSION.
    os.system(f'rm -f {TEST.test_home}/.config/marcel/VERSION')
    expect_exception(lambda: validate_all(TEST.env, validation_error_handler),
                     marcel.exception.KillShellException,
                     'VERSION')


def main_stable():
    test_workspace_lifecycle()
    test_workspaces_and_reservoirs()
    test_workspaces_and_compilables()
    test_workspace_validation()


def main_dev():
    pass


def main():
    TEST.reset_environment()
    main_dev()
    main_stable()
    TEST.report_failures('test_ws')
    sys.exit(TEST.failures)


main()
