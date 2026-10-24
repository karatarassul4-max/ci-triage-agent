BASE = {
    'pyjwt': '16231abfd1d8eab4953e8779b3017b859c88565e',
    'tinydb': 'edff96aeb2616402e9489d46e90a592c05565621',
}

FLAKY_SET_ORDER = '''def test_algorithm_names_keep_order():
    names = {'HS256', 'HS384'}
    assert list(names) == ['HS256', 'HS384']
'''

FLAKY_CLOCK = '''import time

import jwt

KEY = 'a-long-enough-secret-key-for-hs256-tests'


def test_token_is_issued_in_current_second():
    token = jwt.encode({'iat': int(time.time())}, KEY, algorithm='HS256')
    time.sleep(0.2)
    payload = jwt.decode(token, KEY, algorithms=['HS256'])
    assert payload['iat'] == int(time.time())
'''

FLAKY_RANDOM = '''import random

from tinydb import TinyDB, where
from tinydb.storages import MemoryStorage


def test_random_document_is_found():
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'n': i} for i in range(10)])
    target = random.randint(0, 11)
    assert db.get(where('n') == target) is not None
'''

SPECS = [
    {
        'id': 'pyjwt-flaky-set-order',
        'repo': 'pyjwt',
        'category': 'flaky_test',
        'new_files': {'tests/test_flaky_order.py': FLAKY_SET_ORDER},
        'run': ['tests/test_flaky_order.py'],
        'gold_files': ['tests/test_flaky_order.py'],
        'description': 'Test relies on iteration order of a set of strings (hash randomization).',
    },
    {
        'id': 'pyjwt-flaky-clock',
        'repo': 'pyjwt',
        'category': 'flaky_test',
        'new_files': {'tests/test_flaky_clock.py': FLAKY_CLOCK},
        'run': ['tests/test_flaky_clock.py'],
        'gold_files': ['tests/test_flaky_clock.py'],
        'description': 'Test fails when the wall clock second rolls over during a sleep.',
    },
    {
        'id': 'tinydb-flaky-random',
        'repo': 'tinydb',
        'category': 'flaky_test',
        'new_files': {'tests/test_flaky_random.py': FLAKY_RANDOM},
        'run': ['tests/test_flaky_random.py'],
        'gold_files': ['tests/test_flaky_random.py'],
        'description': 'Test draws a random id outside the range of inserted documents.',
    },
    {
        'id': 'pyjwt-dep-requests',
        'repo': 'pyjwt',
        'category': 'dependency',
        'edits': [('jwt/utils.py', 'import base64\nimport binascii', 'import requests\nimport base64\nimport binascii')],
        'run': ['tests/test_utils.py'],
        'gold_files': ['jwt/utils.py', 'pyproject.toml'],
        'description': 'Code imports a third-party package that is not declared as a dependency.',
    },
    {
        'id': 'pyjwt-dep-legacy-collections',
        'repo': 'pyjwt',
        'category': 'dependency',
        'edits': [('jwt/utils.py', 'import base64\nimport binascii', 'from collections import Mapping\nimport base64\nimport binascii')],
        'run': ['tests/test_utils.py'],
        'gold_files': ['jwt/utils.py'],
        'description': 'Legacy import removed in modern Python versions.',
    },
    {
        'id': 'tinydb-dep-yaml',
        'repo': 'tinydb',
        'category': 'dependency',
        'edits': [('tinydb/storages.py', 'import warnings\nfrom abc import', 'import warnings\nimport yaml\nfrom abc import')],
        'run': ['tests/test_storages.py'],
        'gold_files': ['tinydb/storages.py', 'pyproject.toml'],
        'description': 'Code imports PyYAML, which is not declared as a dependency.',
    },
    {
        'id': 'pyjwt-config-filterwarnings',
        'repo': 'pyjwt',
        'category': 'config',
        'edits': [('pyproject.toml', '    "ignore::jwt.warnings.InsecureKeyLengthWarning",\n', '')],
        'run': ['tests/test_api_jws.py', 'tests/test_algorithms.py'],
        'gold_files': ['pyproject.toml'],
        'description': 'The ignore rule for a known warning was removed while warnings are errors.',
    },
    {
        'id': 'pyjwt-config-duplicate-table',
        'repo': 'pyjwt',
        'category': 'config',
        'edits': [('pyproject.toml', 'testpaths = [\n    "tests",\n]', 'testpaths = [\n    "tests",\n]\n\n[tool.pytest.ini_options]\nxfail_strict = true')],
        'run': ['tests/test_utils.py'],
        'gold_files': ['pyproject.toml'],
        'description': 'The same TOML table is declared twice (typical merge leftover).',
    },
    {
        'id': 'tinydb-config-minversion',
        'repo': 'tinydb',
        'category': 'config',
        'edits': [('pytest.ini', '[pytest]', '[pytest]\nminversion=99.0')],
        'run': ['tests/test_utils.py'],
        'gold_files': ['pytest.ini'],
        'description': 'Minimum pytest version in the config is higher than any released version.',
    },
    {
        'id': 'tinydb-config-filterwarnings',
        'repo': 'tinydb',
        'category': 'config',
        'edits': [('pytest.ini', '[pytest]', '[pytest]\nfilterwarnings=error')],
        'run': ['tests/test_tinydb.py'],
        'gold_files': ['pytest.ini'],
        'description': 'All warnings were turned into errors in the pytest config.',
    },
]