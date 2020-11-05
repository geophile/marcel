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

import marcel.util


def ab(namespace):
    """
    Get a dictionary of all the attributes of a namespace.

    Args:
        namespace: (str): write your description
    """
    m = {}
    for key in ('a', 'b'):
        m[key] = namespace.get(key, None)
    return m


namespace = {'a': 10, 'b': 5}
print(f'namespace: {ab(namespace)}')
f = eval('lambda: a + b', namespace)
g = marcel.util.copy(f)
print(f'f globals: {ab(f.__globals__)}')
print(f'g globals: {ab(g.__globals__)}')
print(f'f: {f()}')
print(f'g: {g()}')

namespace['b'] = 20
print(f'namespace: {ab(namespace)}')
print(f'f globals: {ab(f.__globals__)}')
print(f'g globals: {ab(g.__globals__)}')
print(f'f: {f()}')
print(f'g: {g()}')
