from marcel.api import *

recent = select(lambda file: now() - file.mtime < hours(24))
for file in ls('/home/jao/git/marcel') | recent:
    print(f'{file}')
