import os
import pathlib
import shutil

import marcel.main
import marcel.object.error
from marcel.util import *

import test_base

Error = marcel.object.error.Error
start_dir = os.getcwd()
MAIN = marcel.main.Main()
TEST = test_base.Test(MAIN)


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
             expected_out=sorted([absolute('/tmp/test', x) for x in ['sf', 'sd']]))
    TEST.run('ls -0 *f | map (f: f.render_compact())',
             expected_out=sorted([absolute('/tmp/test', x) for x in ['f', 'sf', 'lf']]))
    # Glob in last part of path
    TEST.run('ls -0 /tmp/test/s? | map (f: f.render_compact())',
             expected_out=sorted([absolute('/tmp/test', x) for x in ['sf', 'sd']]))
    TEST.run('ls -0 /tmp/test/*f | map (f: f.render_compact())',
             expected_out=sorted([absolute('/tmp/test', x) for x in ['f', 'sf', 'lf']]))
    # Glob in intermediate part of path
    TEST.run('ls -0 /tmp/test/*d/*dd | map (f: f.render_compact())',
             expected_out=sorted([absolute('/tmp/test', x) for x in [
                 '/tmp/test/d/dd', '/tmp/test/d/sdd', '/tmp/test/sd/dd', '/tmp/test/sd/sdd',
             ]]))
    TEST.run('ls -0 /tmp/test/*f | map (f: f.render_compact())',
             expected_out=sorted([absolute('/tmp/test', x) for x in ['f', 'sf', 'lf']]))
    # Glob identifying duplicates
    TEST.run('ls -0 *f s* | map (f: f.render_compact())',
             expected_out=sorted([absolute('/tmp/test', x) for x in ['f', 'sd', 'sf', 'lf']]))
    # No such file
    TEST.run('ls -0 x | map (f: f.render_compact())',
             expected_out=sorted([]))
    # No such file via glob
    TEST.run('ls -0 x* | map (f: f.render_compact())',
             expected_out=sorted([]))
    # ~ expansion
    TEST.run('ls -0 ~root | map (f: f.path)',
             expected_out=['/root'])


def test_source_and_target_filenames():
    filename_op_setup('/tmp/test')
    # Target must exist
    TEST.run('mv f d x',
             expected_err='Cannot use multiple sources with a non-existent target')
    # Glob target must exist
    TEST.run('mv f d x*',
             expected_err='Cannot use multiple sources with a non-existent target')
    # Multiple targets not allowed
    TEST.run('mv *f *d',
             expected_err='Cannot specify multiple targets')
    # One target works
    TEST.run(test='mv *f d',
             verification='ls -r | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'sd', 'd',  # remaining in top-level dir
                                  'd/sf', 'd/f', 'd/lf',  # moved to d
                                  'sd/sf', 'sd/f', 'sd/lf',  # contents of d also visible in sd
                                  'd/sdf', 'd/df', 'd/ldf', 'd/sdd', 'd/dd',  # originally in d
                                  'sd/sdf', 'sd/df', 'sd/ldf', 'sd/sdd', 'sd/dd',  # via sd also
                                  'd/dd/ddf',  # originally in d/dd
                                  'sd/dd/ddf',  # via sd also
                                  'd/sdd/ddf',  # sdd is a link to dd
                                  'sd/sdd/ddf']))


def test_ls():
    filename_op_setup('/tmp/test')
    # 0/1/r flags with no files specified.
    TEST.run('ls -0 | map (f: f.render_compact())',
             expected_out=sorted(['.'
                                  ]))
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
             expected_out=sorted(['f'
                                  ]))
    TEST.run('ls -1 f | map (f: f.render_compact())',
             expected_out=sorted(['f'
                                  ]))
    TEST.run('ls -r f | map (f: f.render_compact())',
             expected_out=sorted(['f'
                                  ]))
    # 0/1/r flags with directory
    TEST.run('ls -0 /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.'
                                  ]))
    TEST.run('ls -1 /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  ]))
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


def test_rm():
    filename_op_setup('/tmp/test')
    TEST.run('ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
    # Remove one thing (file, link, directory)
    filename_op_setup('/tmp/test')
    TEST.run(test='rm f',
             verification='ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'sf', 'lf', 'd', 'sd']))
    filename_op_setup('/tmp/test')
    TEST.run(test='rm lf',
             verification='ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'd', 'sd']))
    filename_op_setup('/tmp/test')
    TEST.run(test='rm d',
             verification='ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'sd']))
    # Remove symlink to file
    filename_op_setup('/tmp/test')
    TEST.run(test='rm sf',
             verification='ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'lf', 'd', 'sd']))
    # Remove symlink to directory
    filename_op_setup('/tmp/test')
    TEST.run(test='rm sd',
             verification='ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'd']))
    # Remove multiple roots
    filename_op_setup('/tmp/test')
    TEST.run(test='rm s* *d',
             verification='ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'lf']))
    # Remove via piping
    filename_op_setup('/tmp/test')
    TEST.run(test='ls /tmp/test/*f | rm',
             verification='ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'sd', 'd']))
    # Remove non-existent
    filename_op_setup('/tmp/test')
    TEST.run(test='rm x',
             verification='ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
    # Erroneous
    filename_op_setup('/tmp/test')
    TEST.run('ls /tmp/test/*f | rm f',
             expected_err='cannot receive input from a pipe')


def test_mv():
    pass
    # # Move one file to missing target
    # filename_op_setup('/tmp/test')
    # TEST.run(test='mv f t',
    #          verification='ls | map (f: f.render_compact())',
    #          expected_out=sorted(['.', 'sf', 'lf', 'sd', 'd', 't']))
    # # Move one file to file
    # filename_op_setup('/tmp/test')
    # TEST.run(test='echo asdf > g',
    #          verification='ls f g | map (f: (f.name, f.size))',
    #          expected_out=[('f', 2), ('g', 5)])
    # TEST.run(test='mv f g',
    #          verification='ls f g | map (f: (f.name, f.size))',
    #          expected_out=[('g', 2)])
    # # Move one file to dir
    # filename_op_setup('/tmp/test')
    # TEST.run(test='mv f d',
    #          verification='ls d | map (f: f.render_compact())',
    #          expected_out=sorted(['.', 'f', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    # # Move one file to symlink -- FAILS
    # filename_op_setup('/tmp/test')
    # TEST.run(test='mv f sf',
    #          verification='ls -f | map (f: f.render_compact())',
    #          expected_out=sorted(['sf', 'lf']))
    # # Move one file to missing target identified by glob
    # setup(base)
    # TEST.run(test='mv f1 t*',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f2, t_star]))
    # # Move one file to existing file
    # setup(base)
    # TEST.run(test='mv f1 f2',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f2]))
    # # Move one file to existing file identified by glob
    # setup(base)
    # TEST.run(test='mv f1 f2*',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f2]))
    # # Move one file to existing directory
    # setup(base)
    # TEST.run(test='mv f1 d1',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, f1_in_d1, d2, f21, f22, f2]))
    # # Move one file to existing directory identified by glob
    # setup(base)
    # TEST.run(test='mv f1 d1*',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, f1_in_d1, d2, f21, f22, f2]))
    # # Move multiple files to missing target
    # setup(base)
    # TEST.run(test='mv * t',
    #          expected_err='Cannot use multiple sources with a non-existent target')
    # # Move multiple files to missing target identified by glob
    # setup(base)
    # TEST.run(test='mv * t*',
    #          expected_err='Cannot use multiple sources with a non-existent target')
    # # Move multiple files to existing file
    # setup(base)
    # TEST.run(test='mv ?1 f? f1',
    #          expected_err='Cannot use multiple sources with a file target')
    # # Move multiple files to existing file identified by glob
    # setup(base)
    # TEST.run(test='mv ?1 f? f1*',
    #          expected_err='Cannot use multiple sources with a file target')
    # # Move multiple files to existing directory
    # setup(base)
    # TEST.run(test='mv ?2 f? d1',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2_in_d1, f21_in_d1, f22_in_d1, f1_in_d1, f2_in_d1]))
    # # Move multiple files to existing directory identified by glob
    # setup(base)
    # TEST.run(test='mv ?2 f? d1*',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2_in_d1, f21_in_d1, f22_in_d1, f1_in_d1, f2_in_d1]))
    # # Move file to itself
    # setup(base)
    # TEST.run(test='mv f1 f1',
    #          expected_out=[Error('Source and target must be different files')])
    # # Move directory into self. First check the error, then the result
    # setup(base)
    # TEST.run(test='mv d1 d2 d2',
    #          expected_out=[Error('Source and target must be different directories')])
    # setup(base)
    # TEST.run(test='mv d1 d2 d2',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d2, f21, f22, d1_in_d2, f11_in_d2, f12_in_d2, f1, f2]))
    # # Pipe in files to be moved
    # setup(base)
    # TEST.run(test='ls ?2 f? | mv d1',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2_in_d1, f21_in_d1, f22_in_d1, f1_in_d1, f2_in_d1]))


def test_cp():
    def setup(dir):
        TEST.cd(tmp)
        TEST.run('bash rm -rf base')
        TEST.run('mkdir base')
        TEST.cd(base)
        TEST.run('mkdir d')
        TEST.run('echo ddf > d/df')
        TEST.run('echo f > f')
        TEST.run('bash ln f hf')
        TEST.run('bash ln -s f sf')
        TEST.run('bash ln -s d sd')
        TEST.run('bash ln d/df d/hdf')
        TEST.run('bash ln -s df d/sdf')
        TEST.cd(dir)

    dot = '.'
    tmp = '/tmp'
    base = '/tmp/base'
    d = 'd'
    f = 'f'
    hf = 'hf'
    sf = 'sf'
    sd = 'sd'
    df = 'd/df'
    hdf = 'd/hdf'
    sdf = 'd/sdf'
    sddf = 'sd/df'
    sdhdf = 'sd/hdf'
    sdsdf = 'sd/sdf'
    t = 't'
    t_star = 't*'
    # TESTS
    # setup(base)
    # TEST.run(test='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d, f, hf, sf, sd, df, hdf, sdf, sddf, sdhdf, sdsdf]))
    # # Copy one file to missing target
    # setup(base)
    # TEST.run(test='cp f t',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d, f, t, hf, sf, sd, df, hdf, sdf, sddf, sdhdf, sdsdf]))
    # Move one file to missing target identified by glob
    setup(base)
    TEST.run(test='cp f t*',
             verification='ls -r | map (f: f.render_compact())',
             expected_out=sorted([dot, d, f, t_star, hf, sf, sd, df, hdf, sdf, sddf, sdhdf, sdsdf]))
    # # Move one file to existing file
    # setup(base)
    # TEST.run(test='mv f1 f2',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f2]))
    # # Move one file to existing file identified by glob
    # setup(base)
    # TEST.run(test='mv f1 f2*',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f2]))
    # # Move one file to existing directory
    # setup(base)
    # TEST.run(test='mv f1 d1',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, f1_in_d1, d2, f21, f22, f2]))
    # # Move one file to existing directory identified by glob
    # setup(base)
    # TEST.run(test='mv f1 d1*',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, f1_in_d1, d2, f21, f22, f2]))
    # # Move multiple files to missing target
    # setup(base)
    # TEST.run(test='mv * t',
    #          expected_err='Cannot move multiple sources to a non-existent target')
    # # Move multiple files to missing target identified by glob
    # setup(base)
    # TEST.run(test='mv * t*',
    #          expected_err='Cannot move multiple sources to a non-existent target')
    # # Move multiple files to existing file
    # setup(base)
    # TEST.run(test='mv ?1 f? f1',
    #          expected_err='Cannot move multiple sources to a file target')
    # # Move multiple files to existing file identified by glob
    # setup(base)
    # TEST.run(test='mv ?1 f? f1*',
    #          expected_err='Cannot move multiple sources to a file target')
    # # Move multiple files to existing directory
    # setup(base)
    # TEST.run(test='mv ?2 f? d1',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2_in_d1, f21_in_d1, f22_in_d1, f1_in_d1, f2_in_d1]))
    # # Move multiple files to existing directory identified by glob
    # setup(base)
    # TEST.run(test='mv ?2 f? d1*',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2_in_d1, f21_in_d1, f22_in_d1, f1_in_d1, f2_in_d1]))
    # # Move file to itself
    # setup(base)
    # TEST.run(test='mv f1 f1',
    #          expected_out=[Error('Cannot move file over self')])
    # # Move directory into self. First check the error, then the result
    # setup(base)
    # TEST.run(test='mv d1 d2 d2',
    #          expected_out=[Error('Cannot move directory into self')])
    # setup(base)
    # TEST.run(test='mv d1 d2 d2',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d2, f21, f22, d1_in_d2, f11_in_d2, f12_in_d2, f1, f2]))
    # # Pipe in files to be moved
    # setup(base)
    # TEST.run(test='ls ?2 f? | mv d1',
    #          verification='ls -r | map (f: f.render_compact())',
    #          expected_out=sorted([dot, d1, f11, f12, d2_in_d1, f21_in_d1, f22_in_d1, f1_in_d1, f2_in_d1]))


def reset_environment(config_file='./.marcel.py'):
    os.chdir(start_dir)
    MAIN.global_state.env = marcel.env.Environment(config_file)


def main_stable():
    # ls, rm, mv, and cp all extend FilenamesOp, which implements the processing of FILENAME arguments. A FILENAME
    # may be relative or absolute, and it may be a glob pattern. To avoid having to test the intersection of op features
    # with the various possibilities of filename args, testing is organized as follows:
    #    - test_source_filenames(): Test source filename handling using test cases based on ls.
    #    - test_source_and_target_filenames(): Use mv for these tests
    #    - Test op-specific behavior using:
    #         - test_ls
    #         - test_rm
    #         - test_mv
    #         - test_cp
    # All these tests use a common setup, done by filename_op_setup.
    # test_source_filenames()
    # test_source_and_target_filenames()
    # test_ls()
    # test_rm()
    test_mv()
    # test_cp()


def main_dev():
    pass
    # TODO: test_ps()  How?
    # TODO: test cd: absolute, relative, target does not exist


def main():
    reset_environment()
    main_stable()
    main_dev()
    print(f'Test failures: {TEST.failures}')


main()
