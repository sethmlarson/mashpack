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
from mashpack.exceptions import OutOfData, BufferFull, PackValueError, ExtraData
from mashpack import ExtType

if hasattr(sys, 'pypy_version_info'):
    from __pypy__ import newlist_hint
    from __pypy__ import BytesBuilder

    class BytesIO(object):
        def __init__(self, s=b''):
            if s:
                self.builder = BytesBuilder(len(s))
                self.builder.append(s)
            else:
                self.builder = BytesBuilder()

        def write(self, s):
            if isinstance(s, memoryview):
                s = s.tobytes()
            elif isinstance(s, bytearray):
                s = bytes(s)
            self.builder.append(s)

        def getvalue(self):
            return self.builder.build()

    _USING_BYTESBUILDER = True
else:
    from io import BytesIO
    newlist_hint = lambda _: []
    _USING_BYTESBUILDER = False


_DEFAULT_MAX_LEN = 2**31-1
_DEFAULT_NEST_LIMIT = 511

_TYPE_IMMEDIATE = 0
_TYPE_MAP = 1
_TYPE_STR = 2
_TYPE_ARRAY = 3
_TYPE_BIN = 4
_TYPE_MARRAY = 5
_TYPE_EXT = 6

_STRUCT_UINT8 = struct.Struct('B')
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
_STRUCT_EXT16 = struct.Struct('>HB')
_STRUCT_EXT32 = struct.Struct('>IB')

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
    if unpacker._got_extra_data():
        raise ExtraData(ret, unpacker._get_extra_data())
    return ret


class Unpacker(object):
    def __init__(self, file_like=None, *,
                 read_size=0,
                 object_hook=None,
                 object_pairs_hook=None,
                 list_hook=None,
                 ext_hook=ExtType,
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
        self._buffer_i = i + n
        return self._buffer[i:self._buffer_i]

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
            elif second_prefix == 0xE0:
                obj = b - 256

            # FALSE
            elif b == 0xC0:
                obj = False

            # TRUE
            elif b == 0xC1:
                obj = True

            # MAP8
            elif b == 0xC2:
                self._reserve(1)
                n = self._buffer[self._buffer_i]
                self._buffer_i += 1
                if n > self._max_map_len:
                    raise ValueError(f'{n} exceeds max_map_len={self._max_map_len}')
                obj_type = _TYPE_MAP

            # MAP16
            elif b == 0xC3:
                self._reserve(2)
                n, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_map_len:
                    raise ValueError(f'{n} exceeds max_map_len={self._max_map_len}')
                obj_type = _TYPE_MAP

            # MAP32
            elif b == 0xC4:
                self._reserve(4)
                n, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4
                if n > self._max_map_len:
                    raise ValueError(f'{n} exceeds max_map_len={self._max_map_len}')
                obj_type = _TYPE_MAP

            # STR8
            elif b == 0xC5:
                self._reserve(1)
                n = self._buffer[self._buffer_i]
                self._buffer_i += 1
                if n > self._max_str_len:
                    raise ValueError(f'{n} exceeds max_str_len={self._max_str_len}')
                obj = self._read(n)
                obj_type = _TYPE_STR

            # STR16
            elif b == 0xC6:
                self._reserve(2)
                n, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_str_len:
                    raise ValueError(f'{n} exceeds max_str_len={self._max_str_len}')
                obj = self._read(n)
                obj_type = _TYPE_STR

            # STR32
            elif b == 0xC7:
                self._reserve(4)
                n, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4
                if n > self._max_str_len:
                    raise ValueError(f'{n} exceeds max_str_len={self._max_str_len}')
                obj = self._read(n)
                obj_type = _TYPE_STR

            # ARRAY8
            elif b == 0xC8:
                self._reserve(2)
                n, obj_dt = _STRUCT_ARRAY8.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_ARRAY

            # ARRAY16
            elif b == 0xC9:
                self._reserve(3)
                n, obj_dt = _STRUCT_ARRAY16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 3
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_ARRAY

            # ARRAY32
            elif b == 0xCA:
                self._reserve(5)
                n, obj_dt = _STRUCT_ARRAY32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 5
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_ARRAY

            # MARRAY8
            elif b == 0xCB:
                self._reserve(1)
                n = self._buffer[self._buffer_i]
                self._buffer_i += 1
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_MARRAY

            # MARRAY16
            elif b == 0xCC:
                self._reserve(2)
                n, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_MARRAY

            # MARRAY32
            elif b == 0xCD:
                self._reserve(4)
                n, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_MARRAY

            # BIN8
            elif b == 0xCE:
                self._reserve(1)
                n = self._buffer[self._buffer_i]
                self._buffer_i += 1
                if n > self._max_bin_len:
                    raise ValueError(f'{n} exceeds max_bin_len={self._max_bin_len}')
                obj = self._read(n)
                obj_type = _TYPE_BIN

            # BIN16
            elif b == 0xCF:
                self._reserve(2)
                n, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if n > self._max_bin_len:
                    raise ValueError(f'{n} exceeds max_bin_len={self._max_bin_len}')
                obj = self._read(n)
                obj_type = _TYPE_BIN

            # BIN32
            elif b == 0xD0:
                self._reserve(4)
                n, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4
                if n > self._max_bin_len:
                    raise ValueError(f'{n} exceeds max_bin_len={self._max_bin_len}')
                obj = self._read(n)
                obj_type = _TYPE_BIN

            # INT8
            elif b == 0xD1:
                self._reserve(1)
                obj, = _STRUCT_INT8.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 1

            # INT16
            elif b == 0xD2:
                self._reserve(2)
                obj, = _STRUCT_INT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2

            # INT32
            elif b == 0xD3:
                self._reserve(4)
                obj, = _STRUCT_INT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4

            # INT64
            elif b == 0xD4:
                self._reserve(8)
                obj, = _STRUCT_INT64.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 8

            # UINT8
            elif b == 0xD5:
                self._reserve(1)
                obj = self._buffer[self._buffer_i]
                self._buffer_i += 1

            # UINT16
            elif b == 0xD6:
                self._reserve(2)
                obj, = _STRUCT_UINT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2

            # UINT32
            elif b == 0xD7:
                self._reserve(4)
                obj, = _STRUCT_UINT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4

            # UINT64
            elif b == 0xD8:
                self._reserve(8)
                obj, = _STRUCT_UINT64.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 8

            # FLOAT32
            elif b == 0xD9:
                self._reserve(4)
                obj, = _STRUCT_FLOAT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 4

            # FLOAT64
            elif b == 0xDA:
                self._reserve(8)
                obj, = _STRUCT_FLOAT64.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 8

            # EXT8
            elif b == 0xDB:
                self._reserve(2)
                l, n = _STRUCT_EXT8.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 2
                if l > self._max_ext_len:
                    raise ValueError(f'{n} exceeds max_ext_len={self._max_ext_len}')
                obj = self._read(l)
                obj_type = _TYPE_EXT

            # EXT16
            elif b == 0xDC:
                self._reserve(3)
                l, n = _STRUCT_EXT16.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 3
                if l > self._max_ext_len:
                    raise ValueError(f'{n} exceeds max_ext_len={self._max_ext_len}')
                obj = self._read(l)
                obj_type = _TYPE_EXT

            # EXT32
            elif b == 0xDD:
                self._reserve(5)
                l, n = _STRUCT_EXT32.unpack_from(self._buffer, self._buffer_i)
                self._buffer_i += 5
                if l > self._max_ext_len:
                    raise ValueError(f'{n} exceeds max_ext_len={self._max_ext_len}')
                obj = self._read(l)
                obj_type = _TYPE_EXT

            # RESERVED
            elif b == 0xDE:
                pass

            # NULL
            elif b == 0xDF:
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
    def __init__(self, *, default=None,
                 use_float32=False,
                 use_array=False,
                 autoreset=True):
        self._default = default
        self._use_float32 = use_float32
        self._use_array = use_array
        self._autoreset = autoreset

        if default is not None:
            if not callable(default):
                raise TypeError('default must be callable')
        self._default = default

        self._buffer = BytesIO()

    def pack(self, obj) -> bytes:
        try:
            self._pack(obj)
        except:
            self._buffer = BytesIO()
            raise
        ret = self._buffer.getvalue()
        if self._autoreset:
            self._buffer = BytesIO()
        elif _USING_BYTESBUILDER:
            self._buffer = BytesIO(ret)
        return ret

    def pack_map_header(self, n) -> bytes:
        if n >= _DEFAULT_MAX_LEN:
            raise PackValueError()
        self._pack_map_header(n)
        ret = self._buffer.getvalue()
        if self._autoreset:
            self._buffer = BytesIO()
        elif _USING_BYTESBUILDER:
            self._buffer = BytesIO(ret)
        return ret

    def pack_map_pairs(self, pairs) -> bytes:
        self._pack_map_pairs(len(pairs), pairs)
        ret = self._buffer.getvalue()
        if self._autoreset:
            self._buffer = BytesIO()
        elif _USING_BYTESBUILDER:
            self._buffer = BytesIO(ret)
        return ret

    def pack_array_header(self, n) -> bytes:
        if n >= _DEFAULT_MAX_LEN:
            raise PackValueError()
        self._pack_array_header(n)
        ret = self._buffer.getvalue()
        if self._autoreset:
            self._buffer = BytesIO()
        elif _USING_BYTESBUILDER:
            self._buffer = BytesIO(ret)
        return ret

    def pack_ext_header(self, code, n):
        if n >= _DEFAULT_MAX_LEN:
            raise PackValueError()
        self._pack_ext_header(code, n)
        ret = self._buffer.getvalue()
        if self._autoreset:
            self._buffer = BytesIO()
        elif _USING_BYTESBUILDER:
            self._buffer = BytesIO(ret)
        return ret

    def _pack(self, obj, nest_limit=_DEFAULT_NEST_LIMIT):
        default_used = False
        while True:
            if nest_limit < 0:
                raise PackValueError('recursion limit exceeded')

            # Packing NONE
            if obj is None:
                return self._buffer.write(b'\xDF')

            # Packing TRUE
            elif obj is True:
                return self._buffer.write(b'\xC1')

            # Packing FALSE
            elif obj is False:
                return self._buffer.write(b'\xC0')

            # Packing MAP*
            elif isinstance(obj, dict):
                return self._pack_map_pairs(len(obj), obj.items(), nest_limit-1)

            # Packing MARRAY*, TODO: ARRAY
            elif isinstance(obj, list):
                self._pack_array_header(len(obj))
                item_next_limit = nest_limit-1
                for item in obj:
                    self._pack(item, item_next_limit)
                return

            # Packing INT* and UINT*
            elif isinstance(obj, int):
                # Packing UINT*
                if obj >= 0:
                    # Packing INTP
                    if obj <= 0x1F:
                        return self._buffer.write(_STRUCT_UINT8.pack(0xA0 + obj))

                    # Packing UINT8
                    elif obj <= 0xFF:
                        return self._buffer.write(b'\xD5' + _STRUCT_UINT8.pack(obj))

                    # Packing UINT16
                    elif obj <= 0xFFFF:
                        return self._buffer.write(b'\xD6' + _STRUCT_UINT16.pack(obj))

                    # Packing UINT32:
                    elif obj <= 0xFFFFFFFF:
                        return self._buffer.write(b'\xD7' + _STRUCT_UINT32.pack(obj))

                    # Packing UINT64
                    elif obj <= 0xFFFFFFFFFFFFFFFF:
                        return self._buffer.write(b'\xD8' + _STRUCT_UINT64.pack(obj))
                    else:
                        raise PackValueError('integer out of range')

                # Packing NINTP
                elif obj >= -0x20:
                    return self._buffer.write(_STRUCT_UINT8.pack(256 + obj))

                # Packing INT8
                elif obj >= -0x80:
                    return self._buffer.write(b'\xD1' + _STRUCT_INT8.pack(obj))

                # Packing INT16
                elif obj >= -0x8000:
                    return self._buffer.write(b'\xD2' + _STRUCT_INT16.pack(obj))

                # Packing INT32
                elif obj >= -0x80000000:
                    return self._buffer.write(b'\xD3' + _STRUCT_INT32.pack(obj))

                # Packing INT64
                elif obj >= -0x8000000000000000:
                    return self._buffer.write(b'\xD4' + _STRUCT_INT64.pack(obj))

                else:
                    raise PackValueError('integer out of range')

            # Packing STR*
            elif isinstance(obj, str):
                data = obj.encode('utf-8')
                data_len = len(data)

                # Packing STRP
                if data_len <= 0x3F:
                    return self._buffer.write(_STRUCT_UINT8.pack(0x40 + data_len) + data)

                # Packing STR8
                elif data_len <= 0xFF:
                    return self._buffer.write(b'\xC5' + _STRUCT_UINT8.pack(data_len) + data)

                # Packing STR16
                elif data_len <= 0xFFFF:
                    return self._buffer.write(b'\xC6' + _STRUCT_UINT16.pack(data_len) + data)

                # Packing STR32
                elif data_len <= 0xFFFFFFFF:
                    return self._buffer.write(b'\xC7' + _STRUCT_UINT32.pack(data_len) + data)
                else:
                    raise PackValueError('string too large')

            # Packing FLOAT32 and FLOAT64
            elif isinstance(obj, float):
                if self._use_float32:
                    return self._buffer.write(b'\xD9' + _STRUCT_FLOAT32.pack(obj))
                return self._buffer.write(b'\xDA' + _STRUCT_FLOAT64.pack(obj))

            # Packing BIN*
            elif isinstance(obj, (bytes, bytearray)):
                n = len(obj)
                if n >= 2**32:
                    raise PackValueError(f'{type(obj).__name__} is too large')
                self._pack_bin_header(n)
                return self._buffer.write(obj)
            elif isinstance(obj, memoryview):
                n = len(obj) * obj.itemsize
                if n >= 2**32:
                    raise PackValueError('memoryview is too large')
                self._pack_bin_header(n)
                return self._buffer.write(obj)

            # Packing EXT*
            elif isinstance(obj, ExtType):
                self._pack_ext_header(obj.code, len(obj.data))
                return self._buffer.write(obj.data)

            elif not default_used and self._default is not None:
                obj = self._default(obj)
                default_used = True
                continue
            raise TypeError(f'Cannot serialize {obj!r}')

    def _pack_array_header(self, n):
        # Packing MARRAYP
        if 0 < n <= 0x1F:
            return self._buffer.write(_STRUCT_UINT8.pack(0x80 + n))

        # Packing MARRAY8
        elif n <= 0xFF:
            return self._buffer.write(b'\xCB' + _STRUCT_UINT8.pack(n))

        # Packing MARRAY16
        elif n <= 0xFFFF:
            return self._buffer.write(b'\xCC' + _STRUCT_UINT16.pack(n))

        # Packing MARRAY32
        elif n <= 0xFFFFFFFF:
            return self._buffer.write(b'\xCD' + _STRUCT_UINT32.pack(n))
        else:
            raise PackValueError('array too large')

    def _pack_map_header(self, n):
        # Packing MAPP
        if 0 <= n <= 0x3F:
            return self._buffer.write(_STRUCT_UINT8.pack(n))

        # Packing MAP8
        elif n <= 0xFF:
            return self._buffer.write(b'\xC2' + _STRUCT_UINT8.pack(n))

        # Packing MAP16
        elif n <= 0xFFFF:
            return self._buffer.write(b'\xC3' + _STRUCT_UINT16.pack(n))

        # Packing MAP32
        elif n <= 0xFFFFFFFF:
            return self._buffer.write(b'\xC4' + _STRUCT_UINT32.pack(n))
        else:
            raise PackValueError('map too large')

    def _pack_map_pairs(self, n, pairs, nest_limit=_DEFAULT_NEST_LIMIT):
        pair_nest_limit = nest_limit - 1
        self._pack_map_header(n)
        for k, v in pairs:
            self._pack(k, pair_nest_limit)
            self._pack(v, pair_nest_limit)

    def _pack_bin_header(self, n):
        if n <= 0xFF:
            return self._buffer.write(b'\xCE' + _STRUCT_UINT8.pack(n))
        elif n <= 0xFFFF:
            return self._buffer.write(b'\xCF' + _STRUCT_UINT16.pack(n))
        elif n <= 0xFFFFFFFF:
            return self._buffer.write(b'\xD0' + _STRUCT_UINT32.pack(n))
        else:
            raise PackValueError('binary too large')

    def _pack_ext_header(self, code, n):
        if n <= 0xFF:
            return self._buffer.write(b'\xDB')
        elif n <= 0xFFFF:
            return self._buffer.write(b'\xDC')
        elif n <= 0xFFFFFFFF:
            return self._buffer.write(b'\xDD')
        else:
            raise PackValueError('ext too large')
