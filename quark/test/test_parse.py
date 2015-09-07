# Copyright 2015 datawire. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, pytest
from quark.parser import Parser

directory = os.path.join(os.path.dirname(__file__), "parse")

files = [name for name in os.listdir(directory) if name.endswith(".q")]
paths = [os.path.join(directory, name) for name in files]

@pytest.fixture(params=paths)
def path(request):
    return request.param

def test_parse(path):
    text = open(path).read()
    p = Parser()
    ast = p.parse(text)
    astpath = os.path.splitext(path)[0] + ".ast"
    try:
        saved = open(astpath).read()
    except IOError, e:
        saved = None
    computed = str(ast)
    if saved != computed:
        open(astpath + ".cmp", "write").write(computed)
    assert computed == saved