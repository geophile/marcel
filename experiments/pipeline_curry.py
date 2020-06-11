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

# f = lambda e: lambda x: x + e
#
# print(f(10)(4))
#
#
# def f(*args, **kwargs):
#     print(f'args: {args}, kwargs: {kwargs}')
#
#
# f(1, 2, 3)
# f(5, 6, c=4)
# f(1, 2, 3, 4, **{'a': 1, 'b': 2})
#
#
# def g(a, b, c):
#     print(f'a: {a}, b: {b}, c: {c}')
#
# g(**{'a': 1, 'b': 2, 'c': 3})

f = lambda a: lambda x: x + a
g = f(*[], **{'a': 100})
print(g(5))
