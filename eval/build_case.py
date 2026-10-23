import json
import sys
from pathlib import Path

from triage.shell import run

WORKDIR = Path('eval/workdir')
CASES_DIR = Path('eval/cases')


def is_test_file(path):
    p = path.lower()
    name = p.split('/')[-1]
    return (
        p.startswith('tests/')
        or p.startswith('test/')
        or '/tests/' in p
        or name.startswith('test_')
        or name.endswith('_test.py')
    )


def venv_python(name):
    venv = (WORKDIR / ('venv_' + name)).resolve()
    if sys.platform.startswith('win'):
        return str(venv / 'Scripts' / 'python.exe')
    return str(venv / 'bin' / 'python')


def default_branch(repo):
    code, out = run(['git', 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD'], cwd=repo)
    if code == 0:
        return out.strip().replace('origin/', '', 1)
    return 'master'


def clean(repo):
    run(['git', 'reset', '--hard'], cwd=repo)
    run(['git', 'clean', '-fd'], cwd=repo)


def changed_files(repo, parent, fix):
    cmd = ['git', 'diff', '--name-only', '--diff-filter=AM', parent, fix]
    code, out = run(cmd, cwd=repo)
    return [line.strip() for line in out.splitlines() if line.strip()]


def run_tests(python, repo, test_files):
    cmd = [python, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-o', 'addopts='] + test_files
    return run(cmd, cwd=repo)


def parse_failed(output):
    failed = []
    for line in output.splitlines():
        if line.startswith('FAILED '):
            failed.append(line[len('FAILED '):].split(' - ')[0])
    return failed


def make_case(name, short_sha, repo, python):
    code, fix = run(['git', 'rev-parse', short_sha], cwd=repo)
    if code != 0:
        print(short_sha, ': коммит не найден')
        return None
    fix = fix.strip()
    code, parent = run(['git', 'rev-parse', fix + '^'], cwd=repo)
    if code != 0:
        print(short_sha, ': у коммита нет родителя')
        return None
    parent = parent.strip()

    files = changed_files(repo, parent, fix)
    test_files = [f for f in files if f.endswith('.py') and is_test_file(f)]
    src_files = [f for f in files if f.endswith('.py') and not is_test_file(f)]
    if not test_files or not src_files:
        print(short_sha, ': нужен хотя бы один файл кода и один файл тестов')
        return None

    clean(repo)
    run(['git', 'checkout', '-f', parent], cwd=repo)
    run(['git', 'checkout', fix, '--'] + test_files, cwd=repo)
    code_before, log = run_tests(python, repo, test_files)
    if code_before != 1:
        print(short_sha, ': до исправления тесты не упали (код', code_before, ')')
        return None

    clean(repo)
    run(['git', 'checkout', '-f', fix], cwd=repo)
    code_after, _ = run_tests(python, repo, test_files)
    if code_after != 0:
        print(short_sha, ': после исправления тесты не прошли (код', code_after, ')')
        return None

    code, patch = run(['git', 'diff', parent, fix, '--'] + src_files, cwd=repo)
    code, url = run(['git', 'config', '--get', 'remote.origin.url'], cwd=repo)

    case_id = name + '-' + fix[:7]
    case = {
        'id': case_id,
        'source': 'real',
        'repo_url': url.strip(),
        'broken_sha': parent,
        'fix_sha': fix,
        'failing_tests': parse_failed(log),
        'category': 'code_bug',
        'gold_files': src_files,
        'split': 'unassigned',
    }
    return case, log, patch


def save_case(case, log, patch):
    (CASES_DIR / 'logs').mkdir(parents=True, exist_ok=True)
    (CASES_DIR / 'patches').mkdir(parents=True, exist_ok=True)
    case_id = case['id']
    (CASES_DIR / 'logs' / (case_id + '.log')).write_text(log, encoding='utf-8')
    (CASES_DIR / 'patches' / (case_id + '.diff')).write_text(patch, encoding='utf-8')
    text = json.dumps(case, ensure_ascii=False, indent=2)
    (CASES_DIR / (case_id + '.json')).write_text(text, encoding='utf-8')


def main(name, short_shas):
    repo = str((WORKDIR / name).resolve())
    python = venv_python(name)
    branch = default_branch(repo)
    try:
        for short_sha in short_shas:
            result = make_case(name, short_sha, repo, python)
            if result is None:
                continue
            case, log, patch = result
            save_case(case, log, patch)
            print(case['id'], ': кейс сохранён, упавших тестов:', len(case['failing_tests']))
    finally:
        clean(repo)
        run(['git', 'checkout', '-f', branch], cwd=repo)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])