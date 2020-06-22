from marcel.api import *

from marcel.api import *

for file in (ls(file=True, recursive=True) |
             select(lambda file: now() - file.mtime < days(1))):
    print(f'{file}')
