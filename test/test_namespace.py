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

import marcel.namespace


def fail():
    assert False


def check_match(actual, expected):
    assert actual == expected, f'actual: {actual}\nexpected: {expected}'


def test_namespace():
    ns = marcel.namespace.Namespace({'a': 1, 'b': 2})
    try:
        del ns['c']
        fail()
    except KeyError:
        pass
    check_match(ns, {'a': 1, 'b': 2})
    ns.add_frame(['a', 'd', 'e'])
    check_match(ns, {'a': None, 'b': 2, 'd': None, 'e': None})
    ns['a'] = 10
    ns['b'] = 20
    ns['d'] = 30
    check_match(ns, {'a': 10, 'b': 20, 'd': 30, 'e': None})
    ns.remove_frame()
    check_match(ns, {'a': 1, 'b': 20})
    ns.remove_frame()
    check_match(ns, {})
    try:
        ns.remove_frame()
        fail()
    except AssertionError:
        pass


def test_function():
    # Does a namespace work for function definition?
    source = 'lambda a: a + b + c'
    ns = marcel.namespace.Namespace({'b': 1, 'c': 2})
    ns.add_frame({'b', 'c'})
    ns['b'] = 10
    ns['c'] = 20
    f = eval(source, ns)
    check_match(f(1), 31)
    ns.remove_frame()
    check_match(f(100), 103)
    ns['c'] = 5
    check_match(f(100), 106)
    del ns['c']
    try:
        f(1)
        fail()
    except Exception as e:
        pass


def main():
    test_namespace()
    test_function()


main()
