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

import pytest
import hypothesis
from hypothesis.strategies import integers
from mshpck import _decode_varint, _encode_varint, LARGEST_VARINT_COLLECTION


@pytest.mark.parametrize('input,prefix,output', [
    (b'\xFF', 0, 127),
    (b'\x81', 0, 1),
    (b'\x01\x00\x80', 0, 1),
    (b'\xF8', 4, 0),
    (b'\xF8', 3, 8),
    (b'\x00\x81', 1, 64)
])
def test_decode_varint(input, prefix, output):
    decoded_value, consumed = _decode_varint(input, prefix)
    assert decoded_value == output
    assert consumed == len(input)


def test_encode_varint_single_byte():
    assert _encode_varint(1, 3, 0x80) == b'\x91'


@pytest.mark.parametrize('input,prefix,header,output', [
    (0xFF, 0, 0, b'\x7F\x81'),
    (1 << 14, 0, 0, b'\x00\x00\x81'),
    (1 << 7, 1, 0x80, b'\x80\x82'),
    (1 << 49, 0, 0, b'\x00\x00\x00\x00\x00\x00\x00\x81'),
    (1 << 56, 0, 0, b'\x00\x00\x00\x00\x00\x00\x00\x00\x81'),
    (1 << 6, 1, 0, b'\x00\x81')
])
def test_encode_varint_multiple_bytes(input, prefix, header, output):
    assert _encode_varint(input, prefix, header) == output


@hypothesis.given(
    integers(min_value=0, max_value=0xFFFFFFFFFFFFFFFFFFFFFFFF),
    integers(min_value=0, max_value=7)
)
def test_cyclic_encode_and_decode(value, prefix):
    encoded_value = _encode_varint(value, prefix)
    decoded_value, consumed = _decode_varint(encoded_value, prefix)

    assert len(encoded_value) == consumed
    assert decoded_value == value


def test_no_stop_bit_found():
    with pytest.raises(ValueError):
        _decode_varint(b'\x00\x00\x00', 0)


def test_too_big_of_integer_collection_to_decode():
    data = _encode_varint(LARGEST_VARINT_COLLECTION + 1, 0)
    with pytest.raises(ValueError):
        _decode_varint(data, 0, _collection=True)
