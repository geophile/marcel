# This file is part of Marcel.
#
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
# option) any later version.
#
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import pathlib

import marcel.opmodule


def api_source(source_root):
    assert isinstance(source_root, pathlib.Path)
    api_source_path = source_root / 'marcel' / 'api.py'
    with open(api_source_path) as api_source_file:
        api_source = api_source_file.readlines()
    print(api_source[:10])


def main():
    api_source(pathlib.Path('/home/jao/git/marcel'))
    # op_modules = marcel.opmodule.import_op_modules()
    # print(op_modules)
    # for op, mod in op_modules.items():
    #     print(f'{op}: {mod.help()}')


main()
