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

LARGEST_VARINT_COLLECTION = 1 * 1024 * 1024


def packb(obj) -> bytes:
    raise NotImplementedError()


def unpackb(data: bytes):
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
        print(data, total, offset)
    while offset > 0:
        data.insert(0, int.to_bytes(total & 0xFF, 1, 'big'))
        total = total >> 8
        offset -= 1
        print(data, total, offset)

    return b''.join(data)


def _decode_varint(data: bytes, prefix: int, _collection=False) -> int:
    total = 0
    offset = 0
    for i, val in enumerate(data):
        # prefix byte
        if i == 0:
            total += (val & (0x7F >> prefix)) << offset
            if val & (1 << (7 - prefix)):
                break

        # non-prefix byte
        else:
            total |= (val & 0x7F) << offset
            if val & 0x80:
                break

        # memory check
        if total and _collection and total > LARGEST_VARINT_COLLECTION:
                raise ValueError('Detected a large collection and '
                                 'failed decoding for safety purposes.')
        offset += 7
    else:
        raise ValueError('No stop-bit was found for this varint')
    return total
