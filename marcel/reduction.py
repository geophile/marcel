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


def r_plus(acc, x):
    return x if acc is None else acc + x


def r_times(acc, x):
    return x if acc is None else acc * x


def r_xor(acc, x):
    return x if acc is None else acc ^ x


def r_bit_and(acc, x):
    return x if acc is None else acc & x


def r_bit_or(acc, x):
    return x if acc is None else acc | x


def r_and(acc, x):
    return x if acc is None else acc and x


def r_or(acc, x):
    return x if acc is None else acc or x


def r_max(acc, x):
    return x if acc is None else max(acc, x)


def r_min(acc, x):
    return x if acc is None else min(acc, x)


def r_count(acc, x):
    return 1 if acc is None else acc + 1


# Should never be called. Used to identify grouping for the red operator.
def r_group(acc, x):
    assert False
