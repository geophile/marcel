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


class DictSubclass(dict):

    # def __class__(self, *args, **kwargs):
    #     print(f'__class__, args={args}, kwargs={kwargs}')
    #     return super().__class__(*args, **kwargs)

    def __contains__(self, *args, **kwargs):
        print(f'__contains__, args={args}, kwargs={kwargs}')
        return super().__contains__(*args, **kwargs)

    def __delattr__(self, *args, **kwargs):
        print(f'__delattr__, args={args}, kwargs={kwargs}')
        return super().__delattr__(*args, **kwargs)

    def __delitem__(self, *args, **kwargs):
        print(f'__delitem__, args={args}, kwargs={kwargs}')
        return super().__delitem__(*args, **kwargs)

    def __dir__(self, *args, **kwargs):
        print(f'__dir__, args={args}, kwargs={kwargs}')
        return super().__dir__(*args, **kwargs)

    def __doc__(self, *args, **kwargs):
        print(f'__doc__, args={args}, kwargs={kwargs}')
        return super().__doc__(*args, **kwargs)

    def __eq__(self, *args, **kwargs):
        print(f'__eq__, args={args}, kwargs={kwargs}')
        return super().__eq__(*args, **kwargs)

    def __format__(self, *args, **kwargs):
        print(f'__format__, args={args}, kwargs={kwargs}')
        return super().__format__(*args, **kwargs)

    def __ge__(self, *args, **kwargs):
        print(f'__ge__, args={args}, kwargs={kwargs}')
        return super().__ge__(*args, **kwargs)

    def __getattribute__(self, *args, **kwargs):
        print(f'__getattribute__, args={args}, kwargs={kwargs}')
        return super().__getattribute__(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        print(f'__getitem__, args={args}, kwargs={kwargs}')
        return super().__getitem__(*args, **kwargs)

    def __gt__(self, *args, **kwargs):
        print(f'__gt__, args={args}, kwargs={kwargs}')
        return super().__gt__(*args, **kwargs)

    def __hash__(self, *args, **kwargs):
        print(f'__hash__, args={args}, kwargs={kwargs}')
        return super().__hash__(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        print(f'__init__, args={args}, kwargs={kwargs}')
        return super().__init__(*args, **kwargs)

    def __init_subclass__(self, *args, **kwargs):
        print(f'__init_subclass__, args={args}, kwargs={kwargs}')
        return super().__init_subclass__(*args, **kwargs)

    def __iter__(self, *args, **kwargs):
        print(f'__iter__, args={args}, kwargs={kwargs}')
        return super().__iter__(*args, **kwargs)

    def __le__(self, *args, **kwargs):
        print(f'__le__, args={args}, kwargs={kwargs}')
        return super().__le__(*args, **kwargs)

    def __len__(self, *args, **kwargs):
        print(f'__len__, args={args}, kwargs={kwargs}')
        return super().__len__(*args, **kwargs)

    def __lt__(self, *args, **kwargs):
        print(f'__lt__, args={args}, kwargs={kwargs}')
        return super().__lt__(*args, **kwargs)

    def __ne__(self, *args, **kwargs):
        print(f'__ne__, args={args}, kwargs={kwargs}')
        return super().__ne__(*args, **kwargs)

    # def __new__(self, *args, **kwargs):
    #     print(f'__new__, args={args}, kwargs={kwargs}')
    #     return super().__new__(*args, **kwargs)

    def __reduce__(self, *args, **kwargs):
        print(f'__reduce__, args={args}, kwargs={kwargs}')
        return super().__reduce__(*args, **kwargs)

    def __reduce_ex__(self, *args, **kwargs):
        print(f'__reduce_ex__, args={args}, kwargs={kwargs}')
        return super().__reduce_ex__(*args, **kwargs)

    def __repr__(self, *args, **kwargs):
        print(f'__repr__, args={args}, kwargs={kwargs}')
        return super().__repr__(*args, **kwargs)

    def __reversed__(self, *args, **kwargs):
        print(f'__reversed__, args={args}, kwargs={kwargs}')
        return super().__reversed__(*args, **kwargs)

    def __setattr__(self, *args, **kwargs):
        print(f'__setattr__, args={args}, kwargs={kwargs}')
        return super().__setattr__(*args, **kwargs)

    def __setitem__(self, *args, **kwargs):
        print(f'__setitem__, args={args}, kwargs={kwargs}')
        return super().__setitem__(*args, **kwargs)

    def __sizeof__(self, *args, **kwargs):
        print(f'__sizeof__, args={args}, kwargs={kwargs}')
        return super().__sizeof__(*args, **kwargs)

    def __str__(self, *args, **kwargs):
        print(f'__str__, args={args}, kwargs={kwargs}')
        return super().__str__(*args, **kwargs)

    def __subclasshook__(self, *args, **kwargs):
        print(f'__subclasshook__, args={args}, kwargs={kwargs}')
        return super().__subclasshook__(*args, **kwargs)

    def clear(self, *args, **kwargs):
        print(f'clear, args={args}, kwargs={kwargs}')
        return super().clear(*args, **kwargs)

    def copy(self, *args, **kwargs):
        print(f'copy, args={args}, kwargs={kwargs}')
        return super().copy(*args, **kwargs)

    def fromkeys(self, *args, **kwargs):
        print(f'fromkeys, args={args}, kwargs={kwargs}')
        return super().fromkeys(*args, **kwargs)

    def get(self, *args, **kwargs):
        print(f'get, args={args}, kwargs={kwargs}')
        return super().get(*args, **kwargs)

    def items(self, *args, **kwargs):
        print(f'items, args={args}, kwargs={kwargs}')
        return super().items(*args, **kwargs)

    def keys(self, *args, **kwargs):
        print(f'keys, args={args}, kwargs={kwargs}')
        return super().keys(*args, **kwargs)

    def pop(self, *args, **kwargs):
        print(f'pop, args={args}, kwargs={kwargs}')
        return super().pop(*args, **kwargs)

    def popitem(self, *args, **kwargs):
        print(f'popitem, args={args}, kwargs={kwargs}')
        return super().popitem(*args, **kwargs)

    def setdefault(self, *args, **kwargs):
        print(f'setdefault, args={args}, kwargs={kwargs}')
        return super().setdefault(*args, **kwargs)

    def update(self, *args, **kwargs):
        print(f'update, args={args}, kwargs={kwargs}')
        return super().update(*args, **kwargs)

    def values(self, *args, **kwargs):
        print(f'values, args={args}, kwargs={kwargs}')
        return super().values(*args, **kwargs)


print('DEFINE FUNCTION')
source = 'lambda x: x + y'
namespace = DictSubclass()
namespace['y'] = 100
f = eval(source, namespace)
print('RUN FUNCTION')
print(f(5))
namespace['y'] = 200
print(f(5))
print('GLOBALS')
m = f.__globals__.copy()
del m['__builtins__']
print(m)
print('UPDATE')
namespace.update({'a': 1, 'b': 2})
print('KEYS')
namespace.keys()
print('VALUES')
namespace.values()