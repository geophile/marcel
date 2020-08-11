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

import marcel.object.renderable
import marcel.util


class HistoryRecord(marcel.object.renderable.Renderable):

    def __init__(self, id, command):
        self.id = id
        self.command = command
        
    def __eq__(self, other):
        return self.id == other.id
    
    def __ne__(self, other):
        return self.id != other.id
    
    def __lt__(self, other):
        return self.id < other.id
    
    def __le__(self, other):
        return self.id <= other.id
    
    def __gt__(self, other):
        return self.id > other.id
    
    def __ge__(self, other):
        return self.id >= other.id
    
    # Renderable
    
    def render_compact(self):
        return HistoryRecord.format(self.id, self.command)

    def render_full(self, color_scheme):
        return HistoryRecord.format(marcel.util.colorize(self.id, color_scheme.history_id),
                                    marcel.util.colorize(self.command, color_scheme.history_command))

    @staticmethod
    def format(id, command):
        return f'  {id}:  {command}'
