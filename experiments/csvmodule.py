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

import csv


class Receiver:

    def __init__(self):
        """
        Initialize the contents

        Args:
            self: (todo): write your description
        """
        self.contents = []

    def write(self, x):
        """
        Write the given string to the input.

        Args:
            self: (todo): write your description
            x: (todo): write your description
        """
        self.contents.append(x)


receiver = Receiver()
writer = csv.writer(receiver, delimiter=',', quotechar="'", quoting=csv.QUOTE_MINIMAL, lineterminator='')
writer.writerow([123, 456.789, 'abc', 'def ghi', 'mmm, nnn'])
writer.writerow([234, 333, None, 'def ghi', 'mmm, nnn'])
print(receiver.contents)
# for row in receiver.contents:
#     print(row)
