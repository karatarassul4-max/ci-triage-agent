import json
import os
import sys
from pathlib import Path

from eval.build_case import (CASES_DIR, WORKDIR, clean, default_branch,
                             run_tests, save_case, venv_python)
from eval.handmade_specs import BASE, SPECS
from triage.shell import run

FIXED = {
    'GIT_AUTHOR_NAME': 'triage-fixture',
    'GIT_AUTHOR_EMAIL': 'fixture@example.com',
    'GIT_AUTHOR_DATE': '2026-01-01T00:00:00+0000',
    'GIT_COMMITTER_NAME': 'triage-fixture',
    'GIT_COMMITTER_EMAIL': 'fixture@example.com',
    'GIT_COMMITTER_DATE': '2026-01-01T00:00:00+0000',
}
FLAKY_RUNS = 40
MAX_LOG = 60000


def apply_spec(repo, spec):
    touched = []
    for path, old, new in spec.get('edits', []):
        file = Path(repo) / path
        text = file.read_text(encoding='utf-8')
        if text.count(old) != 1:
            raise ValueError(path + ': нужный фрагмент найден ' + str(text.count(old)) + ' раз')
        file.write_text(text.replace(old, new), encoding='utf-8', newline='\n')
        touched.append(path)
    for path, content in spec.get('new_files', {}).items():
        file = Path(repo) / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding='utf-8', newline='\n')
        touched.append(path)
    return touched


def commit_state(repo, spec_id, touched):
    env = dict(os.environ, **FIXED)
    run(['git', 'add', '--'] + touched, cwd=repo, env=env)
    cmd = ['git', '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'fixture: ' + spec_id]
    run(cmd, cwd=repo, env=env)
    code, sha = run(['git', 'rev-parse', 'HEAD'], cwd=repo)
    sha = sha.strip()
    run(['git', 'update-ref', 'refs/triage/' + spec_id, sha], cwd=repo)
    return sha


def parse_failures(output):
    names = []
    for line in output.splitlines():
        for prefix in ('FAILED ', 'ERROR '):
            if line.startswith(prefix):
                names.append(line[len(prefix):].split(' - ')[0])
    return names


def relativize(text, repo):
    roots = [repo, str(WORKDIR.resolve())]
    for root in roots:
        for variant in (root, root.replace(chr(92), '/')):
            for sep in ('/', chr(92)):
                text = text.replace(variant + sep, '')
    return text


def cap_log(text):
    if len(text) <= MAX_LOG:
        return text
    head = text[:40000]
    tail = text[-20000:]
    return head + '\n[... log truncated ...]\n' + tail


def run_flaky(python, repo, files):
    fails = 0
    passes = 0
    first_log = ''
    for i in range(FLAKY_RUNS):
        code, out = run_tests(python, repo, files)
        if code == 0:
            passes += 1
        else:
            fails += 1
            if not first_log:
                first_log = out
    return fails, passes, first_log


def build(spec, repo, python):
    base = BASE[spec['repo']]
    code, out = run(['git', 'cat-file', '-e', base + '^{commit}'], cwd=repo)
    if code != 0:
        print(spec['id'], ': базового коммита нет в клоне')
        return None
    clean(repo)
    run(['git', 'checkout', '-f', base], cwd=repo)
    touched = apply_spec(repo, spec)
    sha = commit_state(repo, spec['id'], touched)

    if spec['category'] == 'flaky_test':
        fails, passes, log = run_flaky(python, repo, spec['run'])
        if fails == 0 or passes == 0:
            print(spec['id'], ': тест не нестабильный (падений', fails, ', успехов', passes, ')')
            return None
        print(spec['id'], ': падений', fails, 'из', FLAKY_RUNS)
    else:
        code, log = run_tests(python, repo, spec['run'])
        if code == 0:
            print(spec['id'], ': тесты не упали')
            return None

    log = cap_log(relativize(log, repo))
    code, patch = run(['git', 'diff', sha, base], cwd=repo)
    code, url = run(['git', 'config', '--get', 'remote.origin.url'], cwd=repo)
    case = {
        'id': spec['id'],
        'repo': spec['repo'],
        'source': 'handmade',
        'repo_url': url.strip(),
        'base_sha': base,
        'broken_sha': sha,
        'fix_sha': None,
        'failing_tests': parse_failures(log),
        'category': spec['category'],
        'gold_files': spec['gold_files'],
        'split': 'unassigned',
        'fix_verified': False,
        'description': spec['description'],
    }
    old = CASES_DIR / (spec['id'] + '.json')
    if old.exists():
        case['split'] = json.loads(old.read_text(encoding='utf-8'))['split']
    return case, log, patch


def main(ids):
    for repo_name in sorted({s['repo'] for s in SPECS}):
        specs = [s for s in SPECS if s['repo'] == repo_name and (not ids or s['id'] in ids)]
        if not specs:
            continue
        repo = str((WORKDIR / repo_name).resolve())
        python = venv_python(repo_name)
        branch = default_branch(repo)
        try:
            for spec in specs:
                result = build(spec, repo, python)
                if result is None:
                    continue
                case, log, patch = result
                save_case(case, log, patch)
                print(case['id'], ': кейс сохранён,', case['category'])
        finally:
            clean(repo)
            run(['git', 'checkout', '-f', branch], cwd=repo)


if __name__ == '__main__':
    main(sys.argv[1:])