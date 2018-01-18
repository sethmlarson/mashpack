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
import mashpack

@pytest.mark.parametrize(
    ['array', 'expected'],
    [([], b'\x80'),
     ([1], b'\x81\xA1'),
     ([1, 2], b'\x82\xA1\xA2'),
     ([1, 2, 3], b'\x83\xA1\xA2\xA3'),
     ([1, 2, 3, 4], b'\x84\xA1\xA2\xA3\xA4')]
)
def test_short_array_always_marrayp(packer, array, expected):
    packer = packer()
    packed = mashpack.packb(array)
    assert packed == expected
    
    
def test_typed_marrayp_requires_3_elements_to_repack_to_array8():
    array = [255] * 2
    packed = mashpack.packb(array)
    assert packed == b'\x84\xF1\xFF\xF1\xFF'

    array = [255] * 3
    packed = mashpack.packb(array)
    assert packed == b'\xE8\x05\xF1\xFF\xFF\xFF'

@pytest.mark.parametrize(
    ['array', 'expected'],
    [([255] * 64, b'\xE8\x40\xF1' + ('\xFF' * 64))]
)
def test_typed_marrayp_packed_to_array8(array, expected):
    packed = mashpack.packb(array)
    assert packed == expected

    
@pytest.mark.parametrize(
    ['array', 'expected'],
    [([0xFF, 0xFFFF, 1], b'\x83\xF1\xFF\xF2\xFF\xFF\xA1')]
)
def test_typed_marrayp_no_change_obj_width(array, expected):
    packed = mashpack.packb(array)
    assert packed == expected
