# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.


class FunctionGlobals(dict):

    def __repr__(self):
        return f'FunctionGlobals({super().__repr__()})'

    def __contains__(self, key):
        print(f'__contains__ {key}')
        return super().__contains__(key)

    def __delitem__(self, key):
        print(f'__delitem__ {key}')
        return super().__delitem__(key)

    def __setitem__(self, *args, **kwargs):
        print(f'__setitem__ {args} {kwargs}')
        return super().__setitem__(*args, **kwargs)

source = 'lambda x: x + y'
namespace = FunctionGlobals()
namespace['y'] = 100
f = eval(source, namespace)
print(f(5))
namespace['y'] = 200
print(f(5))
print(f.__globals__)