# Common processing for ops whose args include FILENAME ...

import os
import pathlib


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


def roots(current_dir, filenames):
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
