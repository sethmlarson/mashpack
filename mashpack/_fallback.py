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

import typing

_DEFAULT_MAX_LEN = 2**31-1
_TYPE_MAP = 1
_TYPE_STR = 2
_TYPE_TARRAY = 3
_TYPE_RAW = 4
_TYPE_ARRAY = 5
_TYPE_BIN = 6
_TYPE_MATRIX = 7
_TYPE_EXT = 8


def unpack(stream, **kwargs):
    data = stream.read()
    return unpackb(data, **kwargs)


def unpackb(data, **kwargs):
    unpacker = Unpacker(None, **kwargs)
    unpacker.feed(data)
    ret = unpacker._unpack()
    return ret


class Unpacker(object):
    def __init__(self, file_like=None,
                 read_size=0,
                 object_hook=None,
                 object_pairs_hook=None,
                 list_hook=None,
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

        self._read_size = read_size
        self._object_hook = object_hook
        self._object_pairs_hook = object_pairs_hook
        self._list_hook = list_hook

        self._max_str_len = max_str_len
        self._max_bin_len = max_bin_len
        self._max_array_len = max_array_len
        self._max_map_len = max_map_len
        self._max_ext_len = max_ext_len

    def _read_header(self):

        # Grabbing the header byte from our buffer
        self._reserve(1)
        b = self._buffer[self._buffer_i]
        self._buffer_i += 1

        n = 0
        obj = None
        obj_type = 0

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
            second_prefix = b & 0x60

            # TARRAYP
            if second_prefix == 0x80:
                n = b & 0x1F
                if n > self._max_array_len:
                    raise ValueError(f'{n} exceeds max_array_len={self._max_array_len}')
                obj_type = _TYPE_ARRAY

            # INTP
            elif second_prefix == 0xA0:
                obj = b & 0x1F
                obj_type = _TYPE_RAW

            # NINTP
            elif second_prefix == 0xB0:
                obj = -(b & 0x1F) - 1
                obj_type = _TYPE_RAW

            else:
                pass  # TODO: Continue from here tomorrow.

        return obj_type, n, obj
