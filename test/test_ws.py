import getpass
import math
import os
import pathlib
import sys

import marcel.main
import marcel.version
import marcel.object.cluster
import marcel.object.error
import marcel.object.workspace
import marcel.version

import test_base

timeit = test_base.timeit
TestDir = test_base.TestDir

Error = marcel.object.error.Error
start_dir = os.getcwd()
TEST = test_base.TestConsole()


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
    ws_default = marcel.object.workspace.Workspace.default()
    ws_restest = marcel.object.workspace.Workspace('restest')
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
    TEST.run(test='f = (lambda: lambda x: x + 1)',
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


def main_stable():
    test_workspace_lifecycle()
    test_workspaces_and_reservoirs()
    test_workspaces_and_compilables()


def main_dev():
    pass


def main():
    TEST.reset_environment()
    main_dev()
    main_stable()
    print(f'Test failures: {TEST.failures}')
    sys.exit(TEST.failures)


main()
