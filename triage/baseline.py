import json
from pathlib import Path

from groq import BadRequestError

from triage.llm import call_model
from triage.metrics import category_correct, file_hit, file_precision, file_recall
from triage.shell import run

WORKDIR = Path('eval/workdir')
LOGS_DIR = Path('eval/cases/logs')
MODEL = 'openai/gpt-oss-20b'

SYSTEM = (
    'You are a CI failure triage assistant. '
    'You receive the output of a failed pytest run. '
    'Find the root cause of the first real error, not its consequences. '
    'Classify it as code_bug, flaky_test, dependency, infra or config. '
    'Name the files that most likely contain the root cause. '
    'This is usually a source file, but for a flaky or broken test it can be the test file, '
    'and for a dependency or configuration problem it can be a config file. '
    'You may infer paths from test names, imports and the traceback. '
    'If you are unsure, lower the confidence. '
    'Answer only by calling submit_diagnosis.'
)

DIAGNOSIS_TOOL = {
    'type': 'function',
    'function': {
        'name': 'submit_diagnosis',
        'description': 'Submit the final diagnosis of the failed test run',
        'parameters': {
            'type': 'object',
            'properties': {
                'category': {
                    'type': 'string',
                    'enum': ['code_bug', 'flaky_test', 'dependency', 'infra', 'config'],
                },
                'root_cause_files': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Paths of files that contain the root cause',
                },
                'explanation': {'type': 'string'},
                'confidence': {'type': 'number', 'description': 'A number from 0 to 1'},
            },
            'required': ['category', 'root_cause_files', 'explanation', 'confidence'],
        },
    },
}


def extract_failure(log, max_lines=60):
    lines = log.splitlines()
    keep = set()
    for i, line in enumerate(lines):
        if 'Error' in line or 'FAILED' in line or line.startswith('E '):
            start = max(0, i - 3)
            end = min(len(lines), i + 4)
            for j in range(start, end):
                keep.add(j)
    chosen = [lines[i] for i in sorted(keep)]
    if not chosen:
        chosen = lines[-max_lines:]
    return '\n'.join(chosen[:max_lines])


def repo_dir(case):
    name = case.get('repo') or case['id'].rsplit('-', 1)[0]
    return str((WORKDIR / name).resolve())


def looks_like_test(path):
    name = path.split('/')[-1]
    return path.startswith('tests/') or '/tests/' in path or name.startswith('test_')


def files_at_commit(repo, sha):
    code, out = run(['git', 'ls-tree', '-r', '--name-only', sha], cwd=repo)
    return set(out.splitlines())


def paths_from_log(log, known_files):
    found = []
    for token in log.split():
        token = token.strip(',:()' + chr(34) + chr(39))
        if '.py' not in token:
            continue
        token = token.split('.py')[0] + '.py'
        parts = token.replace(chr(92), '/').split('/')
        for i in range(len(parts)):
            candidate = '/'.join(parts[i:])
            if candidate in known_files:
                if candidate not in found:
                    found.append(candidate)
                break
    return found


def line_numbers(log, path):
    numbers = []
    needle = path + ':'
    start = 0
    while True:
        i = log.find(needle, start)
        if i == -1:
            break
        j = i + len(needle)
        digits = ''
        while j < len(log) and log[j].isdigit():
            digits += log[j]
            j += 1
        if digits:
            numbers.append(int(digits))
        start = i + 1
    return numbers


def source_snippet(repo, sha, path, log, radius=20):
    code, text = run(['git', 'show', sha + ':' + path], cwd=repo)
    if code != 0:
        return ''
    lines = text.splitlines()
    numbers = line_numbers(log, path)
    center = numbers[-1] if numbers else 1
    start = max(1, center - radius)
    end = min(len(lines), center + radius)
    chunk = [str(i) + ': ' + lines[i - 1] for i in range(start, end + 1)]
    return '\n'.join(chunk)


def source_file_list(repo, sha, limit=80):
    files = sorted(files_at_commit(repo, sha))
    names = [f for f in files if f.endswith('.py') and not looks_like_test(f)]
    return names[:limit]


def build_messages(variant, case, log):
    if variant == 'b0':
        text = log[-5000:]
    else:
        text = extract_failure(log)
    user = 'Failing test log:\n' + text
    if variant == 'b2':
        repo = repo_dir(case)
        known = files_at_commit(repo, case['broken_sha'])
        names = source_file_list(repo, case['broken_sha'])
        user += '\n\nRepository source files:\n' + '\n'.join(names)
        paths = [p for p in paths_from_log(log, known) if not looks_like_test(p)]
        for path in paths[:2]:
            snippet = source_snippet(repo, case['broken_sha'], path, log)
            user += '\n\nSource file ' + path + ':\n' + snippet[:3000]
    return [
        {'role': 'system', 'content': SYSTEM},
        {'role': 'user', 'content': user},
    ]


def diagnose(messages):
    try:
        resp = call_model(
            MODEL,
            messages,
            tools=[DIAGNOSIS_TOOL],
            tool_choice={'type': 'function', 'function': {'name': 'submit_diagnosis'}},
            temperature=0.2,
            max_completion_tokens=1500,
        )
    except BadRequestError as error:
        return 'bad_request', None, 0, str(error)[:500]
    tokens = resp.usage.total_tokens
    calls = resp.choices[0].message.tool_calls
    if not calls:
        return 'no_tool_call', None, tokens, ''
    try:
        diagnosis = json.loads(calls[0].function.arguments)
    except json.JSONDecodeError:
        return 'parse_error', None, tokens, ''
    return 'ok', diagnosis, tokens, ''


def run_variant(variant, case):
    log = (LOGS_DIR / (case['id'] + '.log')).read_text(encoding='utf-8')
    messages = build_messages(variant, case, log)
    status, diagnosis, tokens, error = diagnose(messages)

    result = {
        'case_id': case['id'],
        'variant': variant,
        'model': MODEL,
        'status': status,
        'prediction': diagnosis,
        'category_correct': 0.0,
        'file_hit': 0.0,
        'file_precision': 0.0,
        'file_recall': 0.0,
        'total_tokens': tokens,
        'error': error,
    }
    if status == 'ok':
        files = diagnosis.get('root_cause_files', [])
        if not isinstance(files, list):
            files = []
        files = [f for f in files if str(f).strip()]
        if not files:
            result['status'] = 'empty_answer'
        gold = case['gold_files']
        result['category_correct'] = category_correct(diagnosis.get('category'), case['category'])
        result['file_hit'] = file_hit(files, gold)
        result['file_precision'] = file_precision(files, gold)
        result['file_recall'] = file_recall(files, gold)
    return result