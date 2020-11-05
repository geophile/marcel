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
    """
    Returns the value of x * x *.

    Args:
        acc: (todo): write your description
        x: (todo): write your description
    """
    return x if acc is None else acc + x


def r_times(acc, x):
    """
    Return the times at x.

    Args:
        acc: (str): write your description
        x: (todo): write your description
    """
    return x if acc is None else acc * x


def r_xor(acc, x):
    """
    Return the xor of xor * xor *.

    Args:
        acc: (todo): write your description
        x: (todo): write your description
    """
    return x if acc is None else acc ^ x


def r_bit_and(acc, x):
    """
    Return the value of the bit_bit.

    Args:
        acc: (todo): write your description
        x: (todo): write your description
    """
    return x if acc is None else acc & x


def r_bit_or(acc, x):
    """
    Return the value of x or none if x is not none * x *.

    Args:
        acc: (str): write your description
        x: (todo): write your description
    """
    return x if acc is None else acc | x


def r_and(acc, x):
    """
    Return the value of * x * r * and * x *.

    Args:
        acc: (todo): write your description
        x: (todo): write your description
    """
    return x if acc is None else acc and x


def r_or(acc, x):
    """
    Return the value of x or none if x is not none.

    Args:
        acc: (todo): write your description
        x: (todo): write your description
    """
    return x if acc is None else acc or x


def r_max(acc, x):
    """
    Return the maximum value of x.

    Args:
        acc: (todo): write your description
        x: (int): write your description
    """
    return x if acc is None else max(acc, x)


def r_min(acc, x):
    """
    Return the minimum value of x.

    Args:
        acc: (array): write your description
        x: (array): write your description
    """
    return x if acc is None else min(acc, x)


def r_count(acc, x):
    """
    Return the number of occurrences of x.

    Args:
        acc: (todo): write your description
        x: (todo): write your description
    """
    return 1 if acc is None else acc + 1


# Should never be called. Used to identify grouping for the red operator.
def r_group(acc, x):
    """
    Group the position ] of x - position.

    Args:
        acc: (todo): write your description
        x: (todo): write your description
    """
    assert False
