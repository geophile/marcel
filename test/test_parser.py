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

import marcel.main
import marcel.parser

MAIN = marcel.main.Main(None, same_process=True, old_namespace=None)


def test(text):
    parser = marcel.parser.Parser(text, MAIN.op_modules)
    pipeline = parser.parse()
    print(f'{text} ->\n{pipeline}')


test('gen 5')
test('gen 5 | out')
test('(3)')
test('@jao [ gen 5 ]')
test('!!')
test('!4')
# test('a = 3')
# test('a = (3)')
# test('a = [ls | out]')