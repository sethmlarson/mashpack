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

import os
import re
from setuptools import setup, find_packages


path = os.path.join(os.path.dirname(__file__), 'mashpack', '__about__.py')
with open(path) as f:
    m = re.search('__version__\s+=\s+\'([^\']+)\'', f.read())
    version = m.group(1)


setup(
    name='mashpack',
    version=version,
    packages=find_packages(
        '.', exclude=['tests', 'benchmarks']
    )
)
