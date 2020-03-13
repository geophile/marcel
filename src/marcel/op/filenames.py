# Common processing for ops whose args include FILENAME ...

import os
import pathlib

import marcel.exception


def _normalize_paths(filenames):
    # Resolve ~
    # Resolve . and ..
    # Convert to Path
    # Eliminate duplicates
    paths = []
    path_set = set()  # For avoiding duplicates
    for i in range(len(filenames)):
        # Resolve . and ..
        filename = os.path.normpath(filenames[i])
        # Convert to Path and resolve ~
        path = pathlib.Path(filename).expanduser()
        # Make absolute. Don't use Path.resolve(), which follows symlinks.
        if not path.is_absolute():
            path = pathlib.Path.cwd() / path
        if path not in path_set:
            paths.append(path)
            path_set.add(path)
    return paths


def deglob(current_dir, filenames):
    paths = _normalize_paths(filenames)
    roots = []
    roots_set = set()
    for path in paths:
        if path.exists():
            roots.append(path)
        else:
            path_str = path.as_posix()
            glob_base, glob_pattern = ((pathlib.Path('/'), path_str[1:])
                                       if path.is_absolute() else
                                       (current_dir, path_str))
            for root in glob_base.glob(glob_pattern):
                if root not in roots_set:
                    roots_set.add(root)
                    roots.append(root)
    return roots


# mv and cp have similar argument structure, in which the last syntactic element describes a target,
# and preceding ones describe sources.
def sources_and_target(current_dir, filenames):
    targets = deglob(current_dir, filenames[-1:])
    if len(targets) > 1:
        raise marcel.exception.KillCommandException(f'Cannot specify multiple targets: {filenames[-1]}')
    target = (targets[0] if len(targets) == 1 else pathlib.Path(filenames[-1])).resolve()
    target_path = pathlib.Path(target).resolve()  # Follows symlink if possible
    sources = filenames[:-1]
    if len(sources) == 0:
        if not target_path.is_dir():
            raise marcel.exception.KillCommandException(
                f'{target} must be a directory if files to be moved are provided via input pipe')
        roots = None
    else:
        roots = deglob(current_dir, sources)
        if target_path.exists():
            if target_path.is_file():
                if len(roots) > 1:
                    raise marcel.exception.KillCommandException('Cannot move multiple sources to a file target')
        else:
            if len(roots) > 1:
                raise marcel.exception.KillCommandException('Cannot move multiple sources to a non-existent target')
    return roots, target
