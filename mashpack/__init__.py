# Copyright 2018 Seth Michael Larson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple

__all__ = [
    'Packer', 'Unpacker', 'ExtType',
    'pack', 'packb', 'unpack', 'unpackb',
    'dump', 'dumps', 'load', 'loads'
]


class ExtType(namedtuple('ExtType', ['code', 'data'])):
    def __new__(cls, code, data):
        if not isinstance(code, int):
            raise TypeError('code must be int')
        if not isinstance(data, bytes):
            raise TypeError('data must be bytes')
        if not 0 <= code <= 0x7F:
            raise ValueError('code must be 0 to 127')
        return super(ExtType, cls).__new__(cls, code, data)


from ._fallback import Packer, Unpacker, unpack, unpackb


def pack(o, stream, **kwargs):
    packer = Packer(**kwargs)
    stream.write(packer.pack(o))


def packb(o, **kwargs) -> bytes:
    packer = Packer(**kwargs)
    return packer.pack(o)


# Compatibility with marshal/pickle
load = unpack
loads = unpackb
dump = pack
dumps = packb
