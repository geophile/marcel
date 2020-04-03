import os
import pathlib
import subprocess

TESTDIR = '/tmp/test'
F = pathlib.Path('f.4')
G = pathlib.Path('g.7')
N = pathlib.Path('nothing')
N2 = pathlib.Path('nothing2')
SN = pathlib.Path('sn')
SN2 = pathlib.Path('sn2')
SF = pathlib.Path('sf')
SG = pathlib.Path('sg')
D = pathlib.Path('d')
D_DF = pathlib.Path('d/df.4')
D_F = pathlib.Path('d/f.4')
D_SF = pathlib.Path('d/sf')
N_DF = pathlib.Path('nothing/df.4')
SD = pathlib.Path('sd')
E = pathlib.Path('e')
SE = pathlib.Path('se')
E_D = pathlib.Path('e/d')
E_SD = pathlib.Path('e/sd')
E_SD_DF = pathlib.Path('e/sd/df.4')
E_D_DF = pathlib.Path('e/d/df.4')


def run(command, expected_err=None):
    if expected_err is None:
        os.system(command)
    else:
        process = subprocess.run(command,
                                 shell=True,
                                 executable='/bin/bash',
                                 capture_output=True,
                                 universal_newlines=True)
        actual_out = process.stdout
        actual_err = process.stderr
        if expected_err not in actual_err:
            print(f'Expected: {expected_err}')
            print(f'Actual:   {actual_err}')


def expected_size(p):
    return int(p.suffix[1:])


def size(p):
    return p.stat().st_size


def link_to(link, target):
    return link.is_symlink() and link.resolve().samefile(target)


def setup(test_name):
    print(test_name)
    os.chdir(f'{TESTDIR}/..')
    run(f'rm -rf {TESTDIR}')
    run(f'mkdir {TESTDIR}')
    os.chdir(TESTDIR)
    run(f'echo abc > {F}')  # suffix is size of file
    run(f'echo abcdef > {G}')  # suffix is size of file
    run(f'ln -s {F} {SF}')
    run(f'ln -s {G} {SG}')
    run(f'ln -s {N} {SN}')
    run(f'ln -s {N} {SN2}')
    run(f'mkdir {D}')
    run(f'ln -s {D} {SD}')
    run(f'echo abc > {D_DF}')
    run(f'mkdir {E}')
    run(f'ln -s {E} {SE}')


def nothing_to_nothing():
    setup('nothing_to_nothing')
    run(f'cp {N} {N2}', 'No such file or directory')


def nothing_to_file():
    setup('nothing_to_file')
    run(f'cp {N} {F}', 'No such file or directory')


def nothing_to_dir():
    setup('nothing_to_dir')
    run(f'cp {N} {D}', 'No such file or directory')


def nothing_to_nothinglink():
    setup('nothing_to_nothinglink')
    run(f'cp {N} {SN}', 'No such file or directory')


def nothing_to_filelink():
    setup('nothing_to_filelink')
    run(f'cp {N} {SF}', 'No such file or directory')


def nothing_to_dirlink():
    setup('nothing_to_filelink')
    run(f'cp {N} {SD}', 'No such file or directory')


def file_to_nothing():
    setup('file_to_nothing')
    run(f'cp {F} {N}')
    assert N.exists(), N
    assert size(N) == expected_size(F)


def file_to_file():
    setup('file_to_file')
    run(f'cp {F} {G}')
    assert size(G) == expected_size(F)


def file_to_dir():
    setup('file_to_dir')
    run(f'cp {F} {D}')
    assert D_F.exists(), D_F
    assert size(D_F) == expected_size(D_F)


def file_to_nothinglink():
    setup('file_to_nothinglink')
    run(f'cp {F} {SN}', expected_err='not writing through dangling symlink')


def file_to_filelink():
    setup('file_to_filelink')
    run(f'cp {G} {SF}')
    assert link_to(SF, F)
    assert size(F) == expected_size(G)


def file_to_dirlink():
    setup('file_to_dirlink')
    run(f'cp {F} {SD}')
    assert D_F.exists()
    assert size(D_F) == expected_size(D_F)


def dir_to_nothing():
    setup('dir_to_nothing')
    run(f'cp -r {D} {N}')
    assert N.exists(), N
    assert size(N_DF) == expected_size(N_DF)


def dir_to_file():
    setup('dir_to_file')
    run(f'cp -r {D} {F}', 'cannot overwrite non-directory')


def dir_to_dir():
    setup('dir_to_dir')
    run(f'cp -r {D} {E}')
    assert E_D.exists(), E_D
    assert E_D_DF.exists(), E_D_DF
    assert size(E_D_DF) == expected_size(E_D_DF)


def dir_to_nothinglink():
    setup('dir_to_nothinglink')
    run(f'cp -r {D} {SN}', expected_err='cannot overwrite non-directory')


def dir_to_filelink():
    setup('dir_to_filelink')
    run(f'cp -r {D} {SF}', expected_err='cannot overwrite non-directory')


def dir_to_dirlink():
    setup('dir_to_dirlink')
    run(f'cp -r {D} {SE}')
    assert E_D.exists(), E_D
    assert E_D_DF.exists(), E_D_DF
    assert size(E_D_DF) == expected_size(E_D_DF)


def nothinglink_to_nothing():
    setup('nothinglink_to_nothing')
    run(f'cp {SN} {N2}', 'No such file or directory')


def nothinglink_to_file():
    setup('nothinglink_to_file')
    run(f'cp {SN} {F}', 'No such file or directory')


def nothinglink_to_dir():
    setup('nothinglink_to_dir')
    run(f'cp {SN} {D}', 'No such file or directory')


def nothinglink_to_nothinglink():
    setup('nothinglink_to_nothinglink')
    run(f'cp {SN} {SN2}', 'No such file or directory')


def nothinglink_to_filelink():
    setup('nothinglink_to_filelink')
    run(f'cp {SN} {SF}', 'No such file or directory')


def nothinglink_to_dirlink():
    setup('nothinglink_to_filelink')
    run(f'cp {SN} {SD}', 'No such file or directory')


def filelink_to_nothing():
    def check_file():
        assert N.exists(), N
        assert not N.is_symlink()
        assert size(N) == expected_size(F)

    def check_link():
        assert N.exists(), N
        assert N.is_symlink()
        assert size(N) == expected_size(F)

    for flag, check in {'': check_file,
                        '-H': check_file,
                        '-L': check_file,
                        '-P': check_link}.items():
        setup(f'filelink_to_nothing {flag}')
        run(f'cp {flag} {SF} {N}')
        check()


def filelink_to_file():
    def check_file():
        assert not G.is_symlink()
        assert size(G) == expected_size(F)

    def check_link():
        assert G.exists(), G
        assert G.is_symlink()
        assert size(G) == expected_size(F)

    for flag, check in {'': check_file,
                        '-H': check_file,
                        '-L': check_file,
                        '-P': check_link}.items():
        setup(f'filelink_to_file {flag}')
        run(f'cp {flag} {SF} {G}')
        check()


def filelink_to_dir():
    def check_file():
        assert not D_SF.is_symlink()
        assert size(D_SF) == expected_size(F)

    def check_link():
        assert D_SF.is_symlink()
        try:
            D_SF.resolve(strict=True)
            assert False, D_SF
        except FileNotFoundError:
            pass

    for flag, check in {'': check_file,
                        '-H': check_file,
                        '-L': check_file,
                        '-P': check_link}.items():
        setup(f'filelink_to_dir {flag}')
        run(f'cp {flag} {SF} {D}')
        check()


def filelink_to_nothinglink():
    def check_fail():
        run(f'cp {flag} {SF} {SN}', 'not writing through dangling symlink')

    def check_replace_link():
        run(f'cp {flag} {SF} {SN}')
        assert SN.is_symlink()
        assert link_to(SN, F)
        assert size(SN) == expected_size(F)

    for flag, check in {'': check_fail,
                        '-H': check_fail,
                        '-L': check_fail,
                        '-P': check_replace_link}.items():
        setup(f'filelink_to_nothinglink {flag}')
        check()


def filelink_to_filelink():
    def check_file():
        assert link_to(SG, G)
        assert size(G) == expected_size(F)

    def check_link():
        assert link_to(SG, F)
        assert size(G) == expected_size(G)

    for flag, check in {'': check_file,
                        '-H': check_file,
                        '-L': check_file,
                        '-P': check_link}.items():
        setup(f'filelink_to_filelink {flag}')
        run(f'cp {flag} {SF} {SG}')
        check()


def filelink_to_dirlink():
    def check_file():
        assert D_SF.exists()
        assert not D_SF.is_symlink()
        assert D_SF.is_file()
        assert size(D_SF) == expected_size(F)

    def check_link():
        assert link_to(SD, D)
        assert D_SF.is_symlink()
        try:
            x = D_SF.resolve(strict=True)
            assert False, x
        except FileNotFoundError:
            pass

    for flag, check in {'': check_file,
                        '-H': check_file,
                        '-L': check_file,
                        '-P': check_link}.items():
        setup(f'filelink_to_dirlink {flag}')
        run(f'cp {flag} {SF} {SD}')
        check()


def dirlink_to_nothing():
    def check_dir():
        assert N.exists(), N
        assert not N.is_symlink()
        assert N.is_dir()
        assert size(N_DF) == expected_size(N_DF)

    def check_link():
        assert N.exists(), N
        assert N.is_symlink()
        assert link_to(N, D)

    for flag, check in {'': check_link,
                        '-H': check_dir,
                        '-L': check_dir,
                        '-P': check_link}.items():
        setup(f'dirlink_to_nothing {flag}')
        run(f'cp -r {flag} {SD} {N}')
        check()


def dirlink_to_file():
    def check_dir():
        run(f'cp -r {flag} {SD} {F}', 'cannot overwrite non-directory')

    def check_link():
        run(f'cp -r {flag} {SD} {F}')
        assert F.exists(), F
        assert F.is_symlink()
        assert link_to(F, D)

    for flag, check in {'': check_link,
                        '-H': check_dir,
                        '-L': check_dir,
                        '-P': check_link}.items():
        setup(f'dirlink_to_file {flag}')
        check()


def dirlink_to_dir():
    def check_dir():
        assert not E_SD.is_symlink()
        assert E_SD.is_dir()
        assert E_SD_DF.exists()
        assert size(E_SD_DF) == expected_size(E_SD_DF)

    def check_link():
        assert E_SD.is_symlink()  # Symlink to nothing
        assert not E_SD.exists()  # Reflects the fact that the target does not exist

    for flag, check in {'': check_link,
                        '-H': check_dir,
                        '-L': check_dir,
                        '-P': check_link}.items():
        setup(f'dirlink_to_dir {flag}')
        run(f'cp -r {flag} {SD} {E}')
        check()


def dirlink_to_nothinglink():
    def check_fail():
        run(f'cp -r {flag} {SD} {SN}', 'cannot overwrite non-directory')

    def check_replace_link():
        run(f'cp -r {flag} {SD} {SN}')
        assert SN.is_symlink()
        assert link_to(SN, D)

    for flag, check in {'': check_replace_link,
                        '-H': check_fail,
                        '-L': check_fail,
                        '-P': check_replace_link}.items():
        setup(f'dirlink_to_nothinglink {flag}')
        check()


def dirlink_to_filelink():
    def check_fail():
        run(f'cp -r {flag} {SD} {SF}', 'cannot overwrite non-directory')

    def check_replace_link():
        run(f'cp -r {flag} {SD} {SF}')
        assert SF.is_symlink()
        assert link_to(SF, D)

    for flag, check in {'': check_replace_link,
                        '-H': check_fail,
                        '-L': check_fail,
                        '-P': check_replace_link}.items():
        setup(f'dirlink_to_filelink {flag}')
        check()


def dirlink_to_dirlink():
    def check_link():
        assert link_to(SE, E)
        assert E_SD.is_symlink()
        assert not E_SD.exists()
        try:
            E_SD.resolve(strict=True)
            assert False
        except FileNotFoundError:
            pass

    def check_dir():
        assert link_to(SE, E)
        assert not E_D.is_symlink()
        assert E_SD.is_dir()
        assert E_SD_DF.exists()
        assert size(E_SD_DF) == expected_size(E_SD_DF)

    for flag, check in {'': check_link,
                        '-H': check_dir,
                        '-L': check_dir,
                        '-P': check_link}.items():
        setup(f'dirlink_to_dirlink {flag}')
        run(f'cp -r {flag} {SD} {SE}')
        check()


def main():
    # Copy missing path
    nothing_to_nothing()
    nothing_to_file()
    nothing_to_dir()
    nothing_to_nothinglink()
    nothing_to_filelink()
    nothing_to_dirlink()
    # Copy file
    file_to_nothing()
    file_to_file()
    file_to_dir()
    file_to_nothinglink()
    file_to_filelink()
    file_to_dirlink()
    # Copy dir
    dir_to_nothing()
    dir_to_file()
    dir_to_dir()
    dir_to_nothinglink()
    dir_to_filelink()
    dir_to_dirlink()
    # Copy link-to-missing-path
    nothinglink_to_nothing()
    nothinglink_to_file()
    nothinglink_to_dir()
    nothinglink_to_nothinglink()
    nothinglink_to_filelink()
    nothinglink_to_dirlink()
    # Copy link-to-file
    filelink_to_nothing()
    filelink_to_file()
    filelink_to_dir()
    filelink_to_nothinglink()
    filelink_to_filelink()
    filelink_to_dirlink()
    # Copy link-to-dir
    dirlink_to_nothing()
    dirlink_to_file()
    dirlink_to_dir()
    dirlink_to_nothinglink()
    dirlink_to_filelink()
    dirlink_to_dirlink()


main()
