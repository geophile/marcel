from marcel.api import *

for file in ls(file=True, recursive=True) | select(lambda file: file.suffix == '.py'):
    print(file)