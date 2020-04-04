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
    # Duplicates
    TEST.run('ls -0 *d ? | map (f: f.render_compact())',
             expected_out=sorted([absolute('/tmp/test', x) for x in ['d', 'sd', 'f']]))
    # This should find d twice
    expected = sorted([absolute('/tmp/test', x) for x in ['.', 'f', 'sf', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run('ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)


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
    # Move one file to missing target
    filename_op_setup('/tmp/test')
    TEST.run(test='mv f t',
             verification='ls | map (f: f.render_compact())',
             expected_out=sorted(['.', 'sf', 'lf', 'sd', 'd', 't']))
    # Move one file to file
    filename_op_setup('/tmp/test')
    TEST.run(test='echo asdf > g',
             verification='ls f g | map (f: (f.name, f.size))',
             expected_out=[('f', 2), ('g', 5)])
    TEST.run(test='mv f g',
             verification='ls f g | map (f: (f.name, f.size))',
             expected_out=[('g', 2)])
    # Move one file to dir
    filename_op_setup('/tmp/test')
    TEST.run(test='mv f d',
             verification='ls d | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    # Move one file to symlink
    filename_op_setup('/tmp/test')
    TEST.run(test='mv f sf',
             verification='ls -f | map (f: f.render_compact())',
             expected_out=sorted(['f', 'lf']))
    # Move one dir to missing target
    filename_op_setup('/tmp/test')
    TEST.run(test='mv d t',
             verification='ls | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'sd', 't']))
    # Move one dir to file
    filename_op_setup('/tmp/test')
    TEST.run(test='mv d f',
             expected_out=[Error('File exists')])
    # Move one dir to dir
    filename_op_setup('/tmp/test')
    os.system('mkdir t')
    TEST.run(test='mv d t',
             verification='ls -1 . d t | map (f: f.render_compact())',
             expected_out=sorted([absolute('/tmp/test', x) for x in ['.', 'f', 'sf', 'lf', 'sd', 't', 't/d']]))
    # Move one dir to symlink
    filename_op_setup('/tmp/test')
    TEST.run(test='mv f sf',
             verification='ls -f | map (f: f.render_compact())',
             expected_out=sorted(['f', 'lf']))
    # Move one symlink to missing target
    filename_op_setup('/tmp/test')
    TEST.run(test='mv sf st',
             verification='ls | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'st', 'lf', 'd', 'sd']))
    # Move one symlink to file
    filename_op_setup('/tmp/test')
    TEST.run('echo asdf > g')
    TEST.run(test='mv sf g',
             verification='ls -f | map (f: f.render_compact())',
             expected_out=['f', 'lf'])
    TEST.run(test='ls -s | map (f: f.render_compact())',
             expected_out=sorted(x for x in ['sd', 'g']))
    # Move one symlink to dir
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in ['.', 'f', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['d/sf', 'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='mv sf d',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # Move one symlink to symlink-to-file: Replace target but keep its name.
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in ['.', 'f', 'sf', 'lf', 'd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['sf/df', 'sf/sdf', 'sf/ldf', 'sf/dd', 'sf/sdd']]))
    TEST.run(test='mv sd sf',
             verification='ls -1 . d sf | map (f: f.render_compact())',
             expected_out=expected)
    # Move one symlink to symlink-to-dir: The source goes into the target dir.
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in ['.', 'f', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd', 'd/sf']]))
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd', 'sd/sf']]))
    TEST.run(test='mv sf sd',
             verification='ls -1 . d sd | map (f: f.render_compact())',
             expected_out=expected)
    # Move multiple things to non-existent path
    filename_op_setup('/tmp/test')
    TEST.run(test='mv * x',
             expected_err='Cannot use multiple sources with a non-existent target')
    # Move multiple things to file
    filename_op_setup('/tmp/test')
    TEST.run('echo asdf > t')
    TEST.run(test='mv f lf t',
             expected_err='Cannot use multiple sources with a file target')
    # Move multiple things to dir
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in
                       ['.', 'sf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in
                            ['d/f', 'd/lf', 'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='mv f lf d',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # Move multiple things to symlink-to-file
    filename_op_setup('/tmp/test')
    TEST.run(test='mv f lf sf',
             expected_err='Cannot use multiple sources with a file target')
    # Move multiple things to symlink-to-dir
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in
                       ['.', 'sf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in
                            ['d/f', 'd/lf', 'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='mv f lf sd',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # Move file to self
    filename_op_setup('/tmp/test')
    TEST.run(test='mv f f',
             expected_out=[Error('Source and target must be different files')])
    # Move dir to self
    filename_op_setup('/tmp/test')
    TEST.run(test='mv d d',
             expected_out=[Error('Source and target must be different directories')])
    # Move symlink to self
    filename_op_setup('/tmp/test')
    TEST.run(test='mv sf sf',
             expected_out=[Error('Source and target must be different files')])
    # Move file to symlink pointing to same file
    filename_op_setup('/tmp/test')
    TEST.run(test='mv f sf',
             expected_out=[Error('Source and target must be different files')])
    # Pipe in no files to move
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in
                       ['.', 'f', 'sf', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in
                            ['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='ls x | mv d',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # Pipe in some files to move
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in
                       ['.', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in
                            ['d/f', 'd/sf', 'd/lf', 'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='ls *f | mv d',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # TODO: Move directory to a subdirectory of itself


def test_cp():
    # Copy one file to missing target
    filename_op_setup('/tmp/test')
    TEST.run(test='cp f t',
             verification='ls | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'sd', 'd', 't']))
    # Copy one file to file
    filename_op_setup('/tmp/test')
    TEST.run(test='echo asdf > g',
             verification='ls f g | map (f: (f.name, f.size))',
             expected_out=[('f', 2), ('g', 5)])
    TEST.run(test='cp f g',
             verification='ls f g | map (f: (f.name, f.size))',
             expected_out=[('f', 2), ('g', 2)])
    # Copy one file to dir
    filename_op_setup('/tmp/test')
    TEST.run(test='cp f d',
             verification='ls d | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    # Copy one file to symlink-to-file (copies to target)
    filename_op_setup('/tmp/test')
    TEST.run('echo asdf > g')
    TEST.run(test='cp g sf',
             verification='ls f g | map (f: (f.name, f.size))',
             expected_out=[('f', 5), ('g', 5)])
    # Copy one dir to missing target
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in ['d', 'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['t', 't/df', 't/sdf', 't/ldf', 't/dd', 't/sdd']]))
    TEST.run(test='cp d t',
             verification='ls -1 d t | map (f: f.render_compact())',
             expected_out=expected)
    # Copy one dir to file
    filename_op_setup('/tmp/test')
    TEST.run(test='cp d f',
             expected_out=[Error('Cannot overwrite non-directory')])
    # Copy one dir to dir
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x)
                       for x in ['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']])
    expected.extend(sorted([absolute('/tmp/test', x)
                            for x in ['t/d/df', 't/d/sdf', 't/d/ldf', 't/d/dd', 't/d/sdd']]))
    os.system('mkdir t')
    TEST.run(test='cp d t',
             verification='ls -0 d/* t/d/* | map (f: f.render_compact())',
             expected_out=expected)
    # Copy one dir to symlink (to file)
    filename_op_setup('/tmp/test')
    TEST.run(test='cp d sf',
             expected_out=[Error('Cannot overwrite non-directory')])
    # Copy one dir to symlink (to dir)
    filename_op_setup('/tmp/test')
    TEST.run('cp d e')
    TEST.run(test='cp e sd',
             verification='ls -1 d | map (f: f.render_compact())',
             expected_out=sorted(['.', 'e', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    # Copy one symlink-to-file to missing target
    filename_op_setup('/tmp/test')
    TEST.run(test='cp sf t',
             verification='ls t | map (f: (f.render_compact(), f.is_symlink()))',
             expected_out=[('t', False)])
    # Copy one symlink-to-file to file
    filename_op_setup('/tmp/test')
    TEST.run('echo asdf > g')
    TEST.run(test='cp sf g',
             verification='ls -f g | map (f: (f.render_compact(), f.size))',
             expected_out=[('g', 2)])
    # Copy one symlink-to-file to dir
    filename_op_setup('/tmp/test')
    TEST.run(test='cp sf d',
             verification='ls -f d/sf | map (f: (f.render_compact(), f.size))',
             expected_out=[('sf', 2)])
    # Copy one symlink-to-dir to missing target
    filename_op_setup('/tmp/test')
    TEST.run(test='cp sd t',
             verification='ls -1 t | map (f: f.render_compact())',
             expected_out=sorted(['.', 'df', 'ldf', 'sdf', 'dd', 'sdd']))
    # Copy one symlink-to-dir to file
    filename_op_setup('/tmp/test')
    TEST.run(test='cp sd f',
             verification='ls -s0 f | map (f: f.resolve())',
             expected_out=['/tmp/test/d'])
    # Copy one symlink-to-dir to dir (cyclic not allowed)
    filename_op_setup('/tmp/test')
    TEST.run(test='cp sd d',
             verification='ls -s0 d/sd | map (f: f.render_compact())',
             expected_out=['.'])
    # Copy one symlink-to-dir to dir (OK)
    filename_op_setup('/tmp/test')
    os.system('mkdir e')
    TEST.run(test='cp sd e',
             verification='ls -1 e/sd | map (f: f.render_compact())',
             expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    # Copy one symlink to dir
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in ['.', 'f', 'sf', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['d/sf', 'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='cp sf d',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # Copy one symlink to symlink-to-file: Replace target but keep its name.
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in ['.', 'f', 'sf', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['sf/df', 'sf/sdf', 'sf/ldf', 'sf/dd', 'sf/sdd']]))
    TEST.run(test='cp sd sf',
             verification='ls -1 . d sf | map (f: f.render_compact())',
             expected_out=expected)
    # Copy one symlink to symlink-to-dir: The source goes into the target dir.
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in ['.', 'f', 'sf', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd', 'd/sf']]))
    expected.extend(sorted([absolute('/tmp/test', x) for x in ['sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd', 'sd/sf']]))
    TEST.run(test='cp sf sd',
             verification='ls -1 . d sd | map (f: f.render_compact())',
             expected_out=expected)
    # Copy multiple things to non-existent path
    filename_op_setup('/tmp/test')
    TEST.run(test='cp * x',
             expected_err='Cannot use multiple sources with a non-existent target')
    # Copy multiple things to file
    filename_op_setup('/tmp/test')
    TEST.run('echo asdf > t')
    TEST.run(test='cp f lf t',
             expected_err='Cannot use multiple sources with a file target')
    # Copy multiple things to dir
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in
                       ['.', 'f', 'sf', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in
                            ['d/f', 'd/lf', 'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='cp f lf d',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # Copy multiple things to symlink-to-file
    filename_op_setup('/tmp/test')
    TEST.run(test='cp f lf sf',
             expected_err='Cannot use multiple sources with a file target')
    # Copy multiple things to symlink-to-dir
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in
                       ['.', 'f', 'sf', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in
                            ['d/f', 'd/lf', 'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='cp f lf sd',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # Copy file to self
    filename_op_setup('/tmp/test')
    TEST.run(test='cp f f',
             expected_out=[Error('Source and target must be different files')])
    # Copy dir to self
    filename_op_setup('/tmp/test')
    TEST.run(test='cp d d',
             expected_out=[Error('Source and target must be different directories')])
    # Copy symlink to self
    filename_op_setup('/tmp/test')
    TEST.run(test='cp sf sf',
             expected_out=[Error('same file')])
    # Copy file to symlink pointing to same file
    filename_op_setup('/tmp/test')
    TEST.run(test='cp f sf',
             expected_out=[Error('Source and target must be different files')])
    # Pipe in no files to move
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in
                       ['.', 'f', 'sf', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in
                            ['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='ls x | cp d',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # Pipe in some files to move
    filename_op_setup('/tmp/test')
    expected = sorted([absolute('/tmp/test', x) for x in
                       ['.', 'f', 'sf', 'lf', 'd', 'sd']])
    expected.extend(sorted([absolute('/tmp/test', x) for x in
                            ['d/f', 'd/sf', 'd/lf', 'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']]))
    TEST.run(test='ls *f | cp d',
             verification='ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # TODO: NTA flags, ls flags


def test_cp_bash_behavior():
    # ############ Copy nothing
    filename_op_setup('/tmp/test')
    os.system('ln -s n1 sn1')  # link to nothing
    os.system('ln -s n2 sn2')  # link to nothing
    for target in ('n2', 'f', 'd', 'sn2', 'sf', 'sd'):
        TEST.run(test=f'cp n1 {target}',
                 expected_err='No such file or directory')
    ############ Copy link-to-nothing
    filename_op_setup('/tmp/test')
    os.system('ln -s n1 sn1')  # link to nothing
    os.system('ln -s n2 sn2')  # link to nothing
    for target in ('n2', 'f', 'd', 'sn2', 'sf', 'sd'):
        TEST.run(test=f'cp sn1 {target}',
                 expected_err='No such file or directory')
    # ############ Copy file
    #    target: nothing, file, link to file
    filename_op_setup('/tmp/test')
    os.system('echo asdfasdf > g')
    for target in ('n', 'g', 'sg'):
        TEST.run(test=f'cp f {target}',
                 verification=f'ls {target} | map (f: f.size)',
                 expected_out=[2])
    #    target: dir, link to dir
    os.system('mkdir e')
    for target in ('e', 'sd'):
        TEST.run(test=f'cp f {target}',
                 verification=f'ls {target}/f | map (f: f.size)',
                 expected_out=[2])
    #    target: link to nothing
    filename_op_setup('/tmp/test')
    os.system('ln -s n sn')
    TEST.run(test='cp f sn',
             expected_out=[Error('Cannot write through dangling link')])
    # ############ Copy link to file
    #    target: nothing, file, link to file
    for target in ('n', 'g', 'sg'):
        for flag in ('', '-T', '-A'):
            # Copy the file
            filename_op_setup('/tmp/test')
            os.system('echo asdfasdf > g')
            TEST.run(test=f'cp {flag} sf {target}',
                     verification=f'ls -f {target} | map (f: f.size)',
                     expected_out=[2])
        for flag in ('-N',):
            # Copy the link
            filename_op_setup('/tmp/test')
            os.system('echo asdfasdf > g')
            TEST.run(test=f'cp {flag} sf {target}',
                     verification=f'ls -s {target} | map (f: f.render_compact())',
                     expected_out=[target])
    #    target: dir, link to dir
    for target in ('e', 'sd'):
        for flag in ('', '-T', '-A'):
            filename_op_setup('/tmp/test')
            os.system('mkdir e')
            TEST.run(test=f'cp {flag} sf {target}',
                     verification=f'ls -f {target}/sf | map (f: f.render_compact())',
                     expected_out=[f'sf'])
        for flag in ('-N',):
            filename_op_setup('/tmp/test')
            os.system('mkdir e')
            TEST.run(test=f'cp {flag} sf {target}',
                     verification=f'ls -s {target}/sf | map (f: f.render_compact())',
                     expected_out=[f'sf'])
    #    target: link to nothing
    for flag in ('', '-T', '-A'):
        filename_op_setup('/tmp/test')
        os.system('ln -s n sn')
        TEST.run(test=f'cp {flag} sf sn',
                 expected_out=[Error('Cannot write through dangling link')])
    for flag in ('-N',):
        filename_op_setup('/tmp/test')
        os.system('ln -s n sn')
        TEST.run(test=f'cp {flag} sf sn',
                 verification='ls -s sf | map (f: f.path.resolve())',
                 expected_out=['/tmp/test/f'])
    # ############ Copy dir
    #    target: nothing
    for target in ('n',):
        filename_op_setup('/tmp/test')
        TEST.run(test=f'cp d {target}',
                 verification=f'ls {target} | map (f: f.render_compact())',
                 expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    #    target: dir or link to dir
    for target in ('e', 'se'):
        filename_op_setup('/tmp/test')
        os.system('mkdir e')
        os.system('ln -s e se')
        TEST.run(test=f'cp d {target}',
                 verification=f'ls {target}/d | map (f: f.render_compact())',
                 expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    #    target: link to nothing, file, link to file
    for target in ('sn', 'f', 'sf'):
        filename_op_setup('/tmp/test')
        os.system('ln -s n sn')
        TEST.run(test=f'cp d {target}',
                 expected_out=[Error('Cannot overwrite non-directory')])
    # ############ Copy link to dir
    #    target: nothing
    for target in ('n',):
        for flag in ('-A', '-T'):
            filename_op_setup('/tmp/test')
            TEST.run(test=f'cp {flag} sd {target}',
                     verification=f'ls -0d {target} | map (f: f.render_compact())',
                     expected_out=['.'])
            TEST.run(test=f'ls {target} | map (f: f.render_compact())',
                     expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
        for flag in ('', '-N'):
            filename_op_setup('/tmp/test')
            TEST.run(test=f'cp {flag} sd {target}',
                     verification=f'ls -0s {target} | map (f: f.render_compact())',
                     expected_out=['.'])
            TEST.run(test=f'ls {target} | map (f: f.render_compact())',
                     expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    #    target: dir or link to dir
    for target in ('e', 'se'):
        filename_op_setup('/tmp/test')
        os.system('mkdir e')
        os.system('ln -s e se')
        TEST.run(test=f'cp d {target}',
                 verification=f'ls {target}/d | map (f: f.render_compact())',
                 expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    #    target: link to nothing, file, link to file
    for target in ('sn', 'f', 'sf'):
        filename_op_setup('/tmp/test')
        os.system('ln -s n sn')
        TEST.run(test=f'cp d {target}',
                 expected_out=[Error('Cannot overwrite non-directory')])
    # TODO: Copy dir to existing dir, with some filenames in common between source and target

def test_mkdir():
    filename_op_setup('/tmp/test')
    TEST.run('mkdir a b')


def reset_environment(config_file='./.marcel.py'):
    os.chdir(start_dir)
    MAIN.global_state.env = marcel.env.Environment(config_file)


def main_stable():
    pass
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
    test_source_filenames()
    test_source_and_target_filenames()
    test_ls()
    test_rm()
    test_mv()
    test_cp()
    test_cp_bash_behavior()


def main_dev():
    pass


def main():
    reset_environment()
    main_stable()
    # main_dev()
    print(f'Test failures: {TEST.failures}')


main()
