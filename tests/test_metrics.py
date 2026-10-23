from triage.metrics import (category_correct, file_hit, file_precision,
                            file_recall, normalize_path)


def test_normalize_path():
    assert normalize_path('./src/a.py') == 'src/a.py'
    assert normalize_path('src' + chr(92) + 'a.py') == 'src/a.py'


def test_category_correct():
    assert category_correct('code_bug', 'code_bug') == 1.0
    assert category_correct('infra', 'code_bug') == 0.0


def test_file_hit():
    assert file_hit(['a.py', 'b.py'], ['b.py']) == 1.0
    assert file_hit(['a.py'], ['b.py']) == 0.0
    assert file_hit([], ['b.py']) == 0.0
    assert file_hit(['./b.py'], ['b.py']) == 1.0


def test_precision_recall():
    assert file_precision(['a.py', 'b.py'], ['b.py']) == 0.5
    assert file_recall(['a.py', 'b.py'], ['b.py', 'c.py']) == 0.5
    assert file_precision([], ['b.py']) == 0.0
    assert file_recall(['a.py'], []) == 0.0