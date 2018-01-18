# Copyright 2018 Seth Michael Larson
# Copyright (C) 2008-2011 INADA Naoki <songofacandy@gmail.com>
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
import sys
import typing
from mashpack.exceptions import OutOfData, BufferFull

if hasattr(sys, 'pypy_version_info'):
    from __pypy__ import newlist_hint
else:
    newlist_hint = lambda _: []

_DEFAULT_MAX_LEN = 2**31-1

_TYPE_IMMEDIATE = 0
_TYPE_MAP = 1
_TYPE_STR = 2
_TYPE_ARRAY = 3
_TYPE_BIN = 4
_TYPE_MARRAY = 5
_TYPE_EXT = 6

_STRUCT_UINT16 = struct.Struct('>H')
_STRUCT_UINT32 = struct.Struct('>I')
_STRUCT_UINT64 = struct.Struct('>Q')
_STRUCT_INT8 = struct.Struct('b')
_STRUCT_INT16 = struct.Struct('>h')
_STRUCT_INT32 = struct.Struct('>i')
_STRUCT_INT64 = struct.Struct('>q')
_STRUCT_FLOAT32 = struct.Struct('>f')
_STRUCT_FLOAT64 = struct.Struct('>d')
_STRUCT_ARRAY8 = struct.Struct('>BB')
_STRUCT_ARRAY16 = struct.Struct('>HB')
_STRUCT_ARRAY32 = struct.Struct('>IB')
_STRUCT_EXT8 = struct.Struct('>BB')
_STRUCT_EXT16 = struct.Struct('>IB')
_STRUCT_EXT32 = struct.Struct('>QB')

_CMD_SKIP = 0
_CMD_CONSTRUCT = 1
_CMD_READ_ARRAY_HEADER = 2
_CMD_READ_MAP_HEADER = 3


def _get_data_from_buffer(obj):
    view = memoryview(obj)
    if view.itemsize != 1:
        raise ValueError("cannot unpack from multi-byte object")
    return view


def unpack(stream, **kwargs):
    data = stream.read()
    return unpackb(data, **kwargs)


def unpackb(data, **kwargs):
    unpacker = Unpacker(None, **kwargs)
    unpacker.feed(data)
    ret = unpacker._unpack(_CMD_CONSTRUCT)
    return ret


class Unpacker(object):
    def __init__(self, file_like=None,
                 read_size=0,
                 object_hook=None,
                 object_pairs_hook=None,
                 list_hook=None,
                 ext_hook=None,
                 max_buffer_size=_DEFAULT_MAX_LEN,
                 max_str_len=_DEFAULT_MAX_LEN,
                 max_bin_len=_DEFAULT_MAX_LEN,
                 max_array_len=_DEFAULT_MAX_LEN,
                 max_map_len=_DEFAULT_MAX_LEN,
                 max_ext_len=_DEFAULT_MAX_LEN):

        if file_like is None:
            self._feeding = True
        else:
            if not callable(file_like.read):
                raise TypeError('file.read must be callable')
            self.file_like = file_like
            self._feeding = False

        self._buffer = bytearray()
        self._buffer_i = 0
        self._max_buffer_size = max_buffer_size
        self._stream_offset = 0

        # Index of the last byte that hasn't been used in our buffer.
        self._buffer_used_i = 0

        self._read_size = read_size
        self._object_hook = object_hook
        self._object_pairs_hook = object_pairs_hook
        self._list_hook = list_hook
        self._ext_hook = ext_hook

        self._max_str_len = max_str_len
        self._max_bin_len = max_bin_len
        self._max_array_len = max_array_len
        self._max_map_len = max_map_len
        self._max_ext_len = max_ext_len

    def skip(self):
        self._unpack(_CMD_SKIP)
        self._consume()

    def unpack(self):
        ret = self._unpack(_CMD_CONSTRUCT)
        self._consume()
        return ret

    def read_array_header(self):
        ret = self._unpack(_CMD_READ_ARRAY_HEADER)
        self._consume()
        return ret

    def read_map_header(self):
        ret = self._unpack(_CMD_READ_MAP_HEADER)
        self._consume()
        return ret

    def tell(self):
        return self._stream_offset

    def feed(self, data):
        assert self._feeding
        view = _get_data_from_buffer(data)
        if len(self._buffer) - self._buffer_i + len(view) > self._max_buffer_size:
            raise BufferFull()
        self._buffer += view

    def read_bytes(self, n):
        return self._read(n)

    def _consume(self):
        self._stream_offset += self._buffer_i - self._buffer_used_i
        self._buffer_used_i = self._buffer_i

    def _got_extra_data(self):
        return self._buffer_i < len(self._buffer)

    def _get_extra_data(self):
        return self._buffer[self._buffer_i:]

    def _read(self, n):
        self._reserve(n)
        i = self._buffer_i
        i += n
        self._buffer_i = n
        return self._buffer[i:n]

    def _reserve(self, n):
        remain_bytes = len(self._buffer) - self._buffer_i - n

        # Buffer has n bytes already.
        if remain_bytes >= 0:
            return

        if self._feeding:
            self._buffer_i = self._buffer_used_i
            raise OutOfData()

        # Strip buffer before checkpoint before reading file
        if self._buffer_used_i > 0:
            del self._buffer[:self._buffer_used_i]
            self._buffer_i -= self._buffer_used_i
            self._buffer_used_i = 0

        remain_bytes = -remain_bytes
        while remain_bytes > 0:
            to_read_bytes = max(self._read_size, remain_bytes)
            read_data = self.file_like.read(to_read_bytes)
            if not read_data:
                break
            assert isinstance(read_data, bytes)
            self._buffer += read_data
            remain_bytes -= len(read_data)

        if len(self._buffer) < n + self._buffer_i:
            self._buffer_i = 0  # Rollback
            raise OutOfData()

    def _unpack(self, command: int=_CMD_CONSTRUCT, data_type: typing.Optional[int]=None):
        obj_type, n, obj, obj_dt = self._read_header(data_type)

        # Type checking
        if command == _CMD_READ_ARRAY_HEADER:
            if obj_type != _TYPE_ARRAY and obj_type != _TYPE_MARRAY:
                raise ValueError('Expected ARRAY')
            return n
        elif command == _CMD_READ_MAP_HEADER:
            if obj_type != _TYPE_MAP:
                raise ValueError('Expected MAP')
            return n

        # Unpacking ARRAY
        if obj_type == _TYPE_ARRAY:
            # Skip over every element in the ARRAY
            if command == _CMD_SKIP:
                for _ in range(n):
                    self._unpack(_CMD_SKIP)
                return
            ret = newlist_hint(n)
            for _ in range(n):
                ret.append(self._unpack(_CMD_CONSTRUCT, data_type=obj_dt))
            if self._list_hook is not None:
                ret = self._list_hook(ret)
            return ret

        # Unpacking MARRAY
        elif obj_type == _TYPE_MARRAY:
            if command == _CMD_SKIP:
                for _ in range(n):
                    self._unpack(_CMD_SKIP)
                return
            ret = newlist_hint(n)
            for _ in range(n):
                ret.append(self._unpack(_CMD_CONSTRUCT))
            if self._list_hook is not None:
                ret = self._list_hook(ret)
            return ret

        # Unpacking MAP
        elif obj_type == _TYPE_MAP:
            if command == _CMD_SKIP:
                for _ in range(n):
                    self._unpack(_CMD_SKIP)
                    self._unpack(_CMD_SKIP)
                return
            if self._object_pairs_hook is not None:
                ret = self._object_pairs_hook(
                    (self._unpack(_CMD_CONSTRUCT), self._unpack(_CMD_CONSTRUCT))
                    for _ in range(n)
                )
            else:
                ret = {}
                for _ in range(n):
                    key = self._unpack(_CMD_CONSTRUCT)
                    ret[key] = self._unpack(_CMD_CONSTRUCT)
                if self._object_hook is not None:
                    ret = self._object_hook(ret)
            return ret

        if command == _CMD_SKIP:
            return

        # Unpacking STR
        if obj_type == _TYPE_STR:
            return obj.decode('utf-8')

        # Unpacking BIN
        elif obj_type == _TYPE_BIN:
            return bytes(obj)

        # Unpacking EXT
        elif obj_type == _TYPE_EXT:
            return self._ext_hook(n, bytes(obj))

        # Unpacking INT
        assert obj_type == _TYPE_IMMEDIATE
        return obj

    def _read_header(self, data_type: typing.Optional[int]=None) -> typing.Tuple[int, typing.Optional[int], typing.Any, typing.Optional[int]]:
        # Grabbing the header byte from our buffer
        if data_type is None:
            self._reserve(1)
            b = self._buffer[self._buffer_i]
            self._buffer_i += 1
        else:
            b = data_type

        n = 0
        obj = None
        obj_type = _TYPE_IMMEDIATE
        obj_dt = None  # Only used for ARRAY* types

        first_prefix = b & 0xC0

        # MAPP
        if first_prefix == 0:
            n = b & 0x3F
            if n > self._max_map_len:
                raise ValueError(f'{n} exceeds max_map_len={self._max_str_len}')
            obj_type = _TYPE_MAP

        # STRP
        elif first_prefix == 0x40:
            n = b & 0x3F
            if n > self._max_str_len:
                raise ValueError(f'{n} exceeds max_str_len={self._max_str_len}')
            obj_type = _TYPE_STR
            obj = self._read(n)
        else:
            second_prefix = b & 0xE0

            # MARRAYP
            if second_prefix == 0x80:
                n = b & 0x1F
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_MARRAY

            # INTP
            elif second_prefix == 0xA0:
                obj = b & 0x1F

            # NINTP
            elif second_prefix == 0xB0:
                obj = -(b & 0x1F) - 1

            # FALSE
            elif b == 0xE0:
                obj = False

            # TRUE
            elif b == 0xE1:
                obj = True

            # MAP8
            elif b == 0xE2:
                self._reserve(1)
                n = self._buffer[self._buffer_i]
                self._buffer_i += 1
                if n > self._max_map_len:
                    raise ValueError(f'{n} exceeds max_map_len={self._max_map_len}')
                obj_type = _TYPE_MAP

            # MAP16
            elif b == 0xE3:
                self._reserve(2)
                n, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_map_len:
                    raise ValueError(f'{n} exceeds max_map_len={self._max_map_len}')
                obj_type = _TYPE_MAP

            # MAP32
            elif b == 0xE4:
                self._reserve(4)
                n, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4
                if n > self._max_map_len:
                    raise ValueError(f'{n} exceeds max_map_len={self._max_map_len}')
                obj_type = _TYPE_MAP

            # STR8
            elif b == 0xE5:
                self._reserve(1)
                n = self._buffer[self._buffer_i]
                self._buffer_i += 1
                if n > self._max_str_len:
                    raise ValueError(f'{n} exceeds max_str_len={self._max_str_len}')
                obj = self._read(n)
                obj_type = _TYPE_STR

            # STR16
            elif b == 0xE6:
                self._reserve(2)
                n, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_str_len:
                    raise ValueError(f'{n} exceeds max_str_len={self._max_str_len}')
                obj = self._read(n)
                obj_type = _TYPE_STR

            # STR32
            elif b == 0xE7:
                self._reserve(4)
                n, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4
                if n > self._max_str_len:
                    raise ValueError(f'{n} exceeds max_str_len={self._max_str_len}')
                obj = self._read(n)
                obj_type = _TYPE_STR

            # ARRAY8
            elif b == 0xE8:
                self._reserve(2)
                n, obj_dt = _STRUCT_ARRAY8.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_ARRAY

            # ARRAY16
            elif b == 0xE9:
                self._reserve(3)
                n, obj_dt = _STRUCT_ARRAY16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 3
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_ARRAY

            # ARRAY32
            elif b == 0xEA:
                self._reserve(5)
                n, obj_dt = _STRUCT_ARRAY32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 5
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_ARRAY

            # MARRAY8
            elif b == 0xEB:
                self._reserve(1)
                n = self._buffer[self._buffer_i]
                self._buffer_i += 1
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_MARRAY

            # MARRAY16
            elif b == 0xEC:
                self._reserve(2)
                n, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_MARRAY

            # MARRAY32
            elif b == 0xED:
                self._reserve(4)
                n, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_MARRAY

            # BIN8
            elif b == 0xEE:
                self._reserve(1)
                n = self._buffer[self._buffer_i]
                self._buffer_i += 1
                if n > self._max_bin_len:
                    raise ValueError(f'{n} exceeds max_bin_len={self._max_bin_len}')
                obj = self._read(n)
                obj_type = _TYPE_BIN

            # BIN16
            elif b == 0xEF:
                self._reserve(2)
                n, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_bin_len:
                    raise ValueError(f'{n} exceeds max_bin_len={self._max_bin_len}')
                obj = self._read(n)
                obj_type = _TYPE_BIN

            # BIN32
            elif b == 0xF0:
                self._reserve(4)
                n, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4
                if n > self._max_bin_len:
                    raise ValueError(f'{n} exceeds max_bin_len={self._max_bin_len}')
                obj = self._read(n)
                obj_type = _TYPE_BIN

            # INT8
            elif b == 0xF1:
                self._reserve(1)
                obj, = _STRUCT_INT8.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 1

            # INT16
            elif b == 0xF2:
                self._reserve(2)
                obj, = _STRUCT_INT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2

            # INT32
            elif b == 0xF3:
                self._reserve(4)
                obj, = _STRUCT_INT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4

            # INT64
            elif b == 0xF4:
                self._reserve(8)
                obj, = _STRUCT_INT64.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 8

            # UINT8
            elif b == 0xF5:
                self._reserve(1)
                obj = self._buffer[self._buffer_i]
                self._buffer_i += 1

            # UINT16
            elif b == 0xF6:
                self._reserve(2)
                obj, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2

            # UINT32
            elif b == 0xF7:
                self._reserve(4)
                obj, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4

            # UINT64
            elif b == 0xF8:
                self._reserve(8)
                obj, = _STRUCT_UINT64.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 8

            # FLOAT32
            elif b == 0xF9:
                self._reserve(4)
                obj, = _STRUCT_FLOAT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4

            # FLOAT64
            elif b == 0xFA:
                self._reserve(8)
                obj, = _STRUCT_FLOAT64.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 8

            # EXT8
            elif b == 0xFB:
                self._reserve(2)
                l, n = _STRUCT_EXT8.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if l > self._max_ext_len:
                    raise ValueError(f'{n} exceeds max_ext_len={self._max_ext_len}')
                obj = self._read(l)

            # EXT16
            elif b == 0xFC:
                self._reserve(3)
                l, n = _STRUCT_EXT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 3
                if l > self._max_ext_len:
                    raise ValueError(f'{n} exceeds max_ext_len={self._max_ext_len}')
                obj = self._read(l)

            # EXT32
            elif b == 0xFD:
                self._reserve(5)
                l, n = _STRUCT_EXT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 5
                if l > self._max_ext_len:
                    raise ValueError(f'{n} exceeds max_ext_len={self._max_ext_len}')
                obj = self._read(l)

            # RESERVED
            elif b == 0xFE:
                pass

            # NULL
            elif b == 0xFF:
                obj = None

        return obj_type, n, obj, obj_dt

    def __iter__(self):
        return self

    def __next__(self):
        try:
            ret = self._unpack(_CMD_CONSTRUCT)
            self._consume()
            return ret
        except OutOfData:
            self._consume()
            raise StopIteration


class Packer(object):
    pass
