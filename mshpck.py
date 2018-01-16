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

import struct
import typing

LARGEST_VARINT_COLLECTION = 1 * 1024 * 1024
ARRAY = 0x80
INT = 0xA0
UNUSED = 0xB
MAP = 0xC0
STR = 0xE0
FALSE = 0x00
TRUE = 0x10
FLOAT32 = 0x20
FLOAT64 = 0x30
NULL = 0x40
NEGINT = 0x50
BIN = 0x60
EXT = 0x70


def _packb_obj(obj, encoding='utf-8') -> bytes:
    if isinstance(obj, int):
        if obj > 0:
            return _encode_varint(obj, 3, INT)
        else:
            return _encode_varint(obj * -1, 4, NEGINT)
    elif isinstance(obj, str):
        return _encode_varint(len(obj), 3, STR) + obj.encode(encoding)
    elif obj is False:
        return b'\x00'
    elif obj is True:
        return b'\x10'
    elif isinstance(obj, float):
        return b'\x30' + struct.pack('!d', obj)
    elif obj is None:
        return b'\x40'
    elif isinstance(obj, bytes):
        return _encode_varint(len(obj), 4, BIN) + obj
    elif isinstance(obj, list):
        data = []
        for item in obj:
            data.append(_packb_obj(item, encoding))
        return _encode_varint(len(obj), 4, ARRAY) + b''.join(data)
    elif isinstance(obj, dict):
        data = []
        for key, value in obj.items():
            data.append(_packb_obj(key, encoding))
            data.append(_packb_obj(value, encoding))
        return _encode_varint(len(obj), 4, MAP) + b''.join(data)
    else:
        raise ValueError(f'Unknown object {obj!r}')


def packb(obj, encoding='utf-8') -> bytes:
    return _packb_obj(obj, encoding)


def unpackb(data: bytes, encoding='utf-8'):
    raise NotImplementedError()


def _encode_varint(varint: int, prefix: int, header: int=0) -> bytes:
    if varint < 0:
        raise TypeError('varint must be positive')

    # Single byte encoding
    if ((0x7F >> prefix) & varint) == varint:
        return int.to_bytes(header | varint | (0x80 >> prefix), 1, 'big')

    # Multiple byte encoding
    total = header | (varint & (0x7F >> prefix))
    offset = 1
    varint = varint >> (7 - prefix)
    while varint:
        total = (total << 8) | (varint & 0x7F)
        varint = varint >> 7
        offset += 1
    total |= 0x80

    # Packing data from integer into bytes
    data = []
    while offset >= 4:
        data.insert(0, int.to_bytes(total & 0xFFFFFFFF, 4, 'big'))
        total = total >> 32
        offset -= 4
    while offset > 0:
        data.insert(0, int.to_bytes(total & 0xFF, 1, 'big'))
        total = total >> 8
        offset -= 1

    return b''.join(data)


def _decode_varint(data: bytes, prefix: int, _collection=False) -> typing.Tuple[int, int]:
    total = 0
    offset = 0

    def _memory_check():
        if total and _collection and total > LARGEST_VARINT_COLLECTION:
                raise ValueError('Detected a large collection and '
                                 'failed decoding for safety purposes.')

    for i, val in enumerate(data):
        # Prefix byte
        if i == 0:
            total = (val & (0x7F >> prefix))
            offset = 7 - prefix
            _memory_check()
            if val & (1 << (7 - prefix)):
                break

        # Non-prefix byte
        else:
            total |= (val & 0x7F) << offset
            offset += 7
            _memory_check()
            if val & 0x80:
                break
    else:
        raise ValueError('No stop-bit was found for this varint')
    return total, i + 1


def testme(data):
    import msgpack
    data1 = packb(data)
    data2 = msgpack.packb(data)

    print('mshpck', data1, len(data1))
    print('msgpack', data2, len(data2))
