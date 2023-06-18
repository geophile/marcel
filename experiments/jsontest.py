import json


class _O(object):

    def __repr__(self):
        return str(self.__dict__)


def dict_to_object(j):
    if type(j) is dict:
        o = _O()
        o.__dict__ = j
        return o
    else:
        return j


decoder = json.JSONDecoder(object_hook=dict_to_object)

x = '''{"a": "1", "b": ["c", "d", "e"], "f": {"g": "2"}}'''
x = decoder.decode(x)
print(f'x.a: {x.a}, x.b: {x.b}, x.f.g: {x.f.g}')

