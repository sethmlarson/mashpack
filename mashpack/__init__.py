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

from ._fallback import Packer, Unpacker, unpack, unpackb

__all__ = [
    'Packer', 'Unpacker',
    'pack', 'packb', 'unpack', 'unpackb',
    'dump', 'dumps', 'load', 'loads'
]


def pack(o, stream, **kwargs):
    packer = Packer(**kwargs)
    stream.write(packer.pack(o))


def packb(o, **kwargs):
    packer = Packer(**kwargs)
    return packer.pack(o)


# Compatibility with marshal/pickle
load = unpack
loads = unpackb
dump = pack
dumps = packb