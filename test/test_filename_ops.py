import os
import pathlib
import shutil

import marcel.object.error

import test_base

Error = marcel.object.error.Error
start_dir = os.getcwd()
TEST = test_base.TestConsole()


def relative(base, x):
    x_path = pathlib.Path(x)
    base_path = pathlib.Path(base)
    display_path = x_path.relative_to(base_path)
    return display_path


def absolute(base, x):
    return pathlib.Path(base) / x


def filename_op_setup(dir):
    # test/
    #     f (file)
    #     sf (symlink to f)
    #     lf (hard link to f)
    #     d/ (dir)
    #     sd (symlink to d)
    #         df (file)
    #         sdf (symlink to df)
    #         ldf (hard link to df)
    #         dd/ (dir)
    #         sdd (symlink to dd)
    #             ddf (file)
    setup_script = [
        'rm -rf /tmp/test',
        'mkdir /tmp/test',
        'mkdir /tmp/test/d',
        'echo f > /tmp/test/f',
        'ln -s /tmp/test/f /tmp/test/sf',
        'ln /tmp/test/f /tmp/test/lf',
        'ln -s /tmp/test/d /tmp/test/sd',
        'echo df > /tmp/test/d/df',
        'ln -s /tmp/test/d/df /tmp/test/d/sdf',
        'ln /tmp/test/d/df /tmp/test/d/ldf',
        'mkdir /tmp/test/d/dd',
        'ln -s /tmp/test/d/dd /tmp/test/d/sdd',
        'echo ddf > /tmp/test/d/dd/ddf']
    # Start clean
    TEST.cd('/tmp')
    shutil.rmtree('/tmp/test', ignore_errors=True)
    # Create test data
    for x in setup_script:
        os.system(x)
    TEST.cd(dir)


def test_source_filenames():
    filename_op_setup('/tmp/test')
    # Relative path
    TEST.run('ls . | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
    TEST.run('ls d | map (f: f.render_compact())',
             expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    # Absolute path
    TEST.run('ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
    TEST.run('ls /tmp/test/d | map (f: f.render_compact())',
             expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    # Glob
    TEST.run('ls -0 s? | map (f: f.render_compact())',
             expected_out=sorted(['sf', 'sd']))
    TEST.run('ls -0 *f | map (f: f.render_compact())',
             expected_out=sorted(['f', 'sf', 'lf']))
    # Glob in last part of path
    TEST.run('ls -0 /tmp/test/s? | map (f: f.render_compact())',
             expected_out=sorted(['sf', 'sd']))
    TEST.run('ls -0 /tmp/test/*f | map (f: f.render_compact())',
             expected_out=sorted(['f', 'sf', 'lf']))
    # Glob in intermediate part of path
    TEST.run('ls -0 /tmp/test/*d/*dd | map (f: f.render_compact())',
             expected_out=sorted(['d/dd', 'd/sdd', 'sd/dd', 'sd/sdd']))
    TEST.run('ls -0 /tmp/test/*f | map (f: f.render_compact())',
             expected_out=sorted(['f', 'sf', 'lf']))
    # Glob identifying duplicates
    TEST.run('ls -0 *f s* | map (f: f.render_compact())',
             expected_out=sorted(['f', 'sd', 'sf', 'lf']))
    # No such file
    TEST.run('ls -0 x | map (f: f.render_compact())',
             expected_err='No qualifying paths')
    # No such file via glob
    TEST.run('ls -0 x* | map (f: f.render_compact())',
             expected_err='No qualifying paths')
    # ~ expansion
    TEST.run('ls -0 ~root | map (f: f.path)',
             expected_out=['/root'])


def test_ls():
    filename_op_setup('/tmp/test')
    # 0/1/r flags with no files specified.
    TEST.run('ls -0 | map (f: f.render_compact())',
             expected_out=sorted(['.']))
    TEST.run('ls -1 | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  ]))
    TEST.run('ls -r | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                  'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))
    TEST.run('ls | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  ]))
    # 0/1/r flags with file
    TEST.run('ls -0 f | map (f: f.render_compact())',
             expected_out=sorted(['f']))
    TEST.run('ls -1 f | map (f: f.render_compact())',
             expected_out=sorted(['f']))
    TEST.run('ls -r f | map (f: f.render_compact())',
             expected_out=sorted(['f']))
    # 0/1/r flags with directory
    TEST.run('ls -0 /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.']))
    TEST.run('ls -1 /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'sd', 'd']))
    TEST.run('ls -r /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                  'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))
    # Test f/d/s flags
    TEST.run('ls -fr | map (f: f.render_compact())',
             expected_out=sorted(['f', 'lf',  # Top-level
                                  'd/df', 'd/ldf',  # Contents of d
                                  'sd/df', 'sd/ldf',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))
    TEST.run('ls -dr | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'd',  # Top-level
                                  'd/dd',  # Contents of d
                                  'sd/dd'  # Also reachable via sd
                                  ]))
    TEST.run('ls -sr | map (f: f.render_compact())',
             expected_out=sorted(['sf', 'sd',  # Top-level
                                  'd/sdf', 'd/sdd',  # Contents of d
                                  'sd/sdf', 'sd/sdd'  # Also reachable via sd
                                  ]))
    # Duplicates
    TEST.run('ls -0 *d ? | map (f: f.render_compact())',
             expected_out=sorted(['d', 'sd', 'f']))
    # This should find d twice
    expected = sorted(['.', 'f', 'sf', 'lf', 'd', 'sd'])
    expected.extend(sorted(['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']))
    TEST.run('ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # ls should continue past permission error
    os.system('sudo rm -rf /tmp/lstest')
    os.system('mkdir /tmp/lstest')
    os.system('mkdir /tmp/lstest/d1')
    os.system('mkdir /tmp/lstest/d2')
    os.system('mkdir /tmp/lstest/d3')
    os.system('mkdir /tmp/lstest/d4')
    os.system('touch /tmp/lstest/d1/f1')
    os.system('touch /tmp/lstest/d2/f2')
    os.system('touch /tmp/lstest/d3/f3')
    os.system('touch /tmp/lstest/d4/f4')
    os.system('sudo chown root.root /tmp/lstest/d2')
    os.system('sudo chown root.root /tmp/lstest/d3')
    os.system('sudo chmod 700 /tmp/lstest/d?')
    TEST.run(test='ls -r /tmp/lstest | map (f: f.render_compact())',
             expected_out=['.',
                           'd1',
                           'd1/f1',
                           'd2',
                           Error('Permission denied'),
                           'd3',
                           Error('Permission denied'),
                           'd4',
                           'd4/f4'])
    # Flag-valued args
    TEST.run('TEST = test')
    TEST.run('ls -r /tmp/(TEST) | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                  'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))
    TEST.run('TMP = TMP')
    TEST.run('ls -r /(TMP.lower())/(TEST) | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                  'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))
    # No such file
    TEST.run('ls /nosuchfile',
             expected_err='No qualifying paths')


# pushd, popd, dirs
def test_dir_stack():
    filename_op_setup('/tmp/test')
    TEST.run('mkdir a b c')
    TEST.run('rm -rf p')
    TEST.run('mkdir p')
    TEST.run('chmod 000 p')
    TEST.run(test='pwd | map (f: f.path)',
             expected_out=['/tmp/test'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test'])
    TEST.run(test='pushd a | map (f: f.path)',
             expected_out=['/tmp/test/a', '/tmp/test'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test/a', '/tmp/test'])
    TEST.run(test='pushd ../b | map (f: f.path)',
             expected_out=['/tmp/test/b', '/tmp/test/a', '/tmp/test'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test/b', '/tmp/test/a', '/tmp/test'])
    TEST.run(test='pushd | map (f: f.path)',
             expected_out=['/tmp/test/a', '/tmp/test/b', '/tmp/test'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test/a', '/tmp/test/b', '/tmp/test'])
    TEST.run(test='popd | map (f: f.path)',
             expected_out=['/tmp/test/b', '/tmp/test'])
    TEST.run(test='pwd | map (f: f.path)',
             expected_out=['/tmp/test/b'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test/b', '/tmp/test'])
    TEST.run(test='dirs -c | map (f: f.path)',
             expected_out=['/tmp/test/b'])
    TEST.run(test='pushd | map (f: f.path)',
             expected_out=['/tmp/test/b'])
    # Dir operations when the destination cd does not exist or cannot be entered due to permissions
    # cd
    TEST.run('cd /tmp/test')
    TEST.run(test='cd /tmp/test/doesnotexist',
             expected_err='No such file or directory')
    TEST.run(test='pwd | (f: str(f))',
             expected_out='/tmp/test')
    TEST.run(test='cd /tmp/test/p',
             expected_err='Permission denied')
    TEST.run(test='pwd | (f: str(f))',
             expected_out='/tmp/test')
    # pushd
    TEST.run(test='pushd /tmp/test/doesnotexist',
             expected_err='No such file or directory')
    TEST.run(test='pwd | (f: str(f))',
             expected_out='/tmp/test')
    TEST.run(test='pushd /tmp/test/p',
             expected_err='Permission denied')
    TEST.run(test='pwd | (f: str(f))',
             expected_out='/tmp/test')
    # popd: Arrange for a deleted dir on the stack and try popding into it.
    TEST.run('rm -rf x y')
    TEST.run('mkdir x y')
    TEST.run('cd x')
    TEST.run('pushd ../y | (f: str(f))',
             expected_out=['/tmp/test/y', '/tmp/test/x'])
    TEST.run('rm -rf /tmp/test/x')
    TEST.run('popd',
             expected_err='directories have been removed')
    TEST.run('dirs | (f: str(f))',
             expected_out=['/tmp/test/y'])


def main_stable():
    test_source_filenames()
    test_ls()
    test_dir_stack()


def main_dev():
    pass


def main():
    TEST.reset_environment()
    main_stable()
    # main_dev()
    print(f'Test failures: {TEST.failures}')


main()
