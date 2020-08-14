import os
from marcel.api import *

for file in (ls(os.getcwd(), file=True, recursive=True) |
             select(lambda f: now() - f.mtime < days(1))):
    print(file)
