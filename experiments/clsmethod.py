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


class Base:

    @classmethod
    def f(cls, x):
        return -x


class X(Base):

    @classmethod
    def f(cls, x):
        return x + 100


class Y(Base):

    @classmethod
    def f(cls, x):
        return x + 666000


print(X().f(1))
print(Y().f(1))
